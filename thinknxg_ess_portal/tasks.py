import frappe
from frappe import _
from frappe.utils import today, add_days, getdate, cint, date_diff, now_datetime, add_to_date
from thinknxg_ess_portal.services.notifications import notify


def escalate_tickets():
    from thinknxg_ess_portal.services.sla import escalate_overdue
    escalate_overdue()


def auto_close_resolved_tickets():
    days = cint(frappe.db.get_single_value("ESS Portal Settings", "auto_close_resolved_days")) or 5
    cutoff = add_to_date(now_datetime(), days=-days)
    for name in frappe.get_all("ESS HR Ticket", filters={"status": "Resolved", "resolved_on": ["<", cutoff]},
                               pluck="name"):
        t = frappe.get_doc("ESS HR Ticket", name)
        t.status = "Closed"
        t.flags.ignore_permissions = True
        t.save()
    frappe.db.commit()


def document_expiry_reminders():
    days = cint(frappe.db.get_single_value("ESS Portal Settings", "document_expiry_alert_days")) or 30
    rows = frappe.get_all("ESS Employee Document", fields=["name", "employee", "document_type", "expiry_date",
                                                           "reminder_sent_on"],
                          filters={"expiry_date": ["between", [today(), add_days(today(), days)]]})
    for r in rows:
        if r.reminder_sent_on and date_diff(today(), r.reminder_sent_on) < 7:
            continue
        user = frappe.db.get_value("Employee", r.employee, "user_id")
        notify(user, "Documents", _("{0} expires on {1}").format(_(r.document_type), r.expiry_date),
               _("Please renew it and upload the new copy."), "/ess/documents", "ESS Employee Document", r.name)
        frappe.db.set_value("ESS Employee Document", r.name, "reminder_sent_on", today(), update_modified=False)
    frappe.db.commit()


def policy_ack_reminders():
    from thinknxg_ess_portal.api.policies import _pending_for
    for emp in frappe.get_all("Employee", filters={"status": "Active", "user_id": ["is", "set"]},
                              fields=["name", "user_id", "company", "department", "branch", "designation"]):
        pending = _pending_for(emp)
        overdue = [p for p in pending if p.get("overdue")]
        if overdue:
            notify(emp.user_id, "Announcements", _("{0} policy acknowledgement(s) overdue").format(len(overdue)),
                   ", ".join(p["policy_title"] for p in overdue[:3]), "/ess/documents?tab=policies")
    frappe.db.commit()


def award_rule_badges():
    badges = frappe.get_all("ESS Badge", filters={"is_active": 1, "rule_type": ["!=", "Manual"]},
                            fields=["name", "rule_type", "threshold"])
    if not badges:
        return
    employees = frappe.get_all("Employee", filters={"status": "Active"},
                               fields=["name", "user_id", "date_of_joining"])
    awarded = {(a.employee, a.badge) for a in frappe.get_all("ESS Badge Award", fields=["employee", "badge"])}

    def count(rule, emp):
        if rule == "Recognitions Received":
            return frappe.db.count("ESS Recognition", {"recipient": emp.name, "status": "Approved"})
        if rule == "Recognitions Given":
            return frappe.db.count("ESS Recognition", {"sender": emp.user_id, "status": "Approved"}) if emp.user_id else 0
        if rule == "Policies Acknowledged":
            return frappe.db.count("ESS Policy Acknowledgement", {"employee": emp.name})
        if rule == "Training Completed" and frappe.db.exists("DocType", "Training Result Employee"):
            return frappe.db.count("Training Result Employee", {"employee": emp.name, "docstatus": 1})
        if rule == "Onboarding Completed" and frappe.db.exists("DocType", "Employee Onboarding"):
            return frappe.db.count("Employee Onboarding", {"employee": emp.name, "boarding_status": "Completed"})
        if rule == "Work Anniversary" and emp.date_of_joining:
            return date_diff(today(), emp.date_of_joining) // 365
        return 0

    for b in badges:
        for emp in employees:
            if (emp.name, b.name) in awarded:
                continue
            if count(b.rule_type, emp) >= (b.threshold or 1):
                try:
                    frappe.get_doc({"doctype": "ESS Badge Award", "employee": emp.name, "badge": b.name,
                                    "source": "Rule", "awarded_by": "Administrator",
                                    "reason": _("Automatically awarded: {0}").format(_(b.rule_type))
                                    }).insert(ignore_permissions=True)
                except frappe.DuplicateEntryError:
                    pass
    frappe.db.commit()


def purge_ai_history():
    days = cint(frappe.db.get_single_value("ESS Portal Settings", "ai_retention_days")) or 90
    cutoff = add_days(today(), -days)
    frappe.db.delete("ESS AI Message Audit", {"creation": ["<", cutoff]})
    for name in frappe.get_all("ESS AI Conversation", filters={"last_message_on": ["<", cutoff],
                                                               "retention_status": "Active"}, pluck="name"):
        frappe.db.set_value("ESS AI Conversation", name, {"retention_status": "Purged", "title": "(purged)"})
        frappe.cache.delete_value(f"ess_ai_hist:{name}")
    frappe.db.commit()


def build_analytics_snapshots():
    from thinknxg_ess_portal.services.analytics import build_snapshots
    build_snapshots()
    frappe.db.commit()


def sync_delegation_shares():
    """Give active delegates read/write share on documents waiting for their delegator, and revoke expired."""
    from frappe.share import add as share_add, remove as share_remove
    active = frappe.get_all("ESS Approval Delegation", filters={"is_active": 1, "from_date": ["<=", today()],
                                                                "to_date": [">=", today()]},
                            fields=["name", "delegator", "delegate", "include_leave", "include_expense"])
    for d in active:
        if d.include_leave:
            for n in frappe.get_all("Leave Application", filters={"leave_approver": d.delegator, "docstatus": 0,
                                                                  "status": "Open"}, pluck="name"):
                share_add("Leave Application", n, d.delegate, read=1, write=1, submit=1, notify=0, flags={"ignore_share_permission": True})
        if d.include_expense:
            for n in frappe.get_all("Expense Claim", filters={"expense_approver": d.delegator, "docstatus": 0},
                                    pluck="name"):
                share_add("Expense Claim", n, d.delegate, read=1, write=1, submit=1, notify=0, flags={"ignore_share_permission": True})
    expired = frappe.get_all("ESS Approval Delegation", filters={"to_date": ["<", today()], "is_active": 1},
                             fields=["name", "delegator", "delegate"])
    for d in expired:
        for dt, field in (("Leave Application", "leave_approver"), ("Expense Claim", "expense_approver")):
            for n in frappe.get_all(dt, filters={field: d.delegator}, pluck="name", limit=500):
                try:
                    share_remove(dt, n, d.delegate, flags={"ignore_share_permission": True})
                except Exception:
                    pass
        frappe.db.set_value("ESS Approval Delegation", d.name, "is_active", 0)
    frappe.db.commit()
