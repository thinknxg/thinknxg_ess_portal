import frappe
from frappe import _
from frappe.utils import cint
from thinknxg_ess_portal.api._guard import guard, parse

EVENTS = ["Approvals", "Leave", "Attendance", "Payroll", "Expenses", "Helpdesk", "Documents", "Recognition",
          "Announcements", "Assistant"]
CHANNELS = ["In App", "Email", "Push"]


@frappe.whitelist(methods=["GET"])
def list_notifications(limit=30, unread_only=0):
    guard(employee=False)
    flt = {"for_user": frappe.session.user}
    if cint(unread_only):
        flt["read"] = 0
    return frappe.get_all("Notification Log", filters=flt, order_by="creation desc", limit=min(cint(limit) or 30, 100),
                          fields=["name", "subject", "email_content", "document_type", "document_name", "read",
                                  "creation"])


@frappe.whitelist(methods=["POST"])
def mark_read(names=None, all=0):
    guard(employee=False)
    flt = {"for_user": frappe.session.user, "read": 0}
    if not cint(all):
        flt["name"] = ["in", parse(names, []) or [""]]
    for n in frappe.get_all("Notification Log", filters=flt, pluck="name"):
        frappe.db.set_value("Notification Log", n, "read", 1, update_modified=False)
    return {"unread": frappe.db.count("Notification Log", {"for_user": frappe.session.user, "read": 0})}


@frappe.whitelist(methods=["GET"])
def get_preferences():
    guard(employee=False)
    from thinknxg_ess_portal.services.notifications import DEFAULTS
    stored = {(p.event_type, p.channel): p.enabled for p in frappe.get_all(
        "ESS Notification Preference", filters={"user": frappe.session.user}, fields=["event_type", "channel", "enabled"])}
    return {"events": EVENTS, "channels": CHANNELS,
            "matrix": {e: {c: bool(stored.get((e, c), DEFAULTS[c])) for c in CHANNELS} for e in EVENTS}}


@frappe.whitelist(methods=["POST"])
def set_preference(event_type, channel, enabled):
    guard(employee=False)
    if event_type not in EVENTS or channel not in CHANNELS:
        frappe.throw(_("Invalid preference"))
    name = frappe.db.get_value("ESS Notification Preference", {"user": frappe.session.user, "event_type": event_type,
                                                                "channel": channel})
    if name:
        frappe.db.set_value("ESS Notification Preference", name, "enabled", cint(enabled))
    else:
        frappe.get_doc({"doctype": "ESS Notification Preference", "user": frappe.session.user, "event_type": event_type,
                        "channel": channel, "enabled": cint(enabled)}).insert(ignore_permissions=True)
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def push_subscribe(subscription):
    guard(employee=False)
    sub = parse(subscription, {})
    endpoint = sub.get("endpoint")
    if not endpoint or not endpoint.startswith("https://"):
        frappe.throw(_("Invalid subscription"))
    keys = sub.get("keys") or {}
    name = frappe.db.get_value("ESS Push Subscription", {"user": frappe.session.user, "endpoint": endpoint})
    if name:
        frappe.db.set_value("ESS Push Subscription", name, "is_active", 1)
    else:
        frappe.get_doc({"doctype": "ESS Push Subscription", "user": frappe.session.user, "endpoint": endpoint,
                        "p256dh": keys.get("p256dh"), "auth": keys.get("auth"),
                        "user_agent": (frappe.get_request_header("User-Agent") or "")[:140]}).insert(ignore_permissions=True)
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def push_unsubscribe(endpoint):
    guard(employee=False)
    for n in frappe.get_all("ESS Push Subscription", filters={"user": frappe.session.user, "endpoint": endpoint},
                            pluck="name"):
        frappe.db.set_value("ESS Push Subscription", n, "is_active", 0)
    return {"ok": True}
