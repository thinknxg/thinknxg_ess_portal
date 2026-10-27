import frappe
from frappe.utils import cint

DEFAULTS = {"In App": True, "Email": False, "Push": True}


def _pref(user, event_type, channel):
    v = frappe.db.get_value("ESS Notification Preference",
                            {"user": user, "event_type": event_type, "channel": channel}, "enabled")
    return DEFAULTS[channel] if v is None else bool(cint(v))


def notify(user, event_type, subject, message="", route="/ess", ref_doctype=None, ref_name=None):
    if not user or user in ("Guest", "Administrator"):
        return
    try:
        if _pref(user, event_type, "In App"):
            frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert",
                            "subject": subject, "email_content": message,
                            "document_type": ref_doctype, "document_name": ref_name,
                            "from_user": frappe.session.user}).insert(ignore_permissions=True)
        frappe.publish_realtime("ess_notification", {"subject": subject, "message": message, "route": route,
                                                     "event_type": event_type}, user=user, after_commit=True)
        if _pref(user, event_type, "Email"):
            frappe.sendmail(recipients=[user], subject=subject,
                            message=f"<p>{frappe.utils.escape_html(message)}</p>"
                                    f"<p><a href='{frappe.utils.get_url(route)}'>Open in ESS Portal</a></p>")
        if _pref(user, event_type, "Push"):
            frappe.enqueue("thinknxg_ess_portal.services.notifications.send_push", user=user, title=subject,
                           body=message[:180], route=route, queue="short", enqueue_after_commit=True)
    except Exception:
        frappe.log_error(title="ESS notify failed")


def send_push(user, title, body, route):
    """Web Push via VAPID. Optional: requires `pywebpush` and VAPID keys in settings.
    Payload never contains confidential values - only a title and a route."""
    try:
        from pywebpush import webpush, WebPushException  # noqa: F401
    except ImportError:
        return
    s = frappe.get_cached_doc("ESS Portal Settings")
    private_key = s.get_password("vapid_private_key", raise_exception=False)
    if not (private_key and s.vapid_public_key):
        return
    import json
    for sub in frappe.get_all("ESS Push Subscription", filters={"user": user, "is_active": 1},
                              fields=["name", "endpoint", "p256dh", "auth"]):
        try:
            webpush(subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                    data=json.dumps({"title": title, "body": body, "route": route}),
                    vapid_private_key=private_key, vapid_claims={"sub": s.vapid_subject or "mailto:hr@example.com"})
        except Exception as e:
            if "410" in str(e) or "404" in str(e):
                frappe.db.set_value("ESS Push Subscription", sub.name, "is_active", 0)
