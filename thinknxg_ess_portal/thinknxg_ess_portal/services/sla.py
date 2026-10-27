import frappe
from frappe import _
from frappe.utils import now_datetime
from thinknxg_ess_portal.services.notifications import notify


def escalate_overdue():
    now = now_datetime()
    rows = frappe.db.sql("""
        select name from `tabESS HR Ticket`
        where status not in ('Resolved','Closed','Waiting for Employee')
          and ((resolution_due < %(now)s) or (first_responded_on is null and first_response_due < %(now)s))
          and coalesce(escalation_level,0) < 3
    """, {"now": now}, pluck=True)
    for name in rows:
        t = frappe.get_doc("ESS HR Ticket", name)
        cat = frappe.get_cached_doc("ESS HR Ticket Category", t.category)
        level = (t.escalation_level or 0) + 1
        target = cat.escalation_user
        if level >= 2 or not target:
            managers = frappe.get_all("Has Role", filters={"role": "HR Manager", "parenttype": "User"},
                                      pluck="parent", limit=5)
            target_list = [m for m in managers if m not in ("Administrator",)]
        else:
            target_list = [target]
        t.db_set({"escalated": 1, "escalation_level": level, "sla_status": "Breached"}, update_modified=False)
        frappe.get_doc({"doctype": "ESS HR Ticket Comment", "ticket": name, "via": "System", "is_internal": 1,
                        "author": "Administrator",
                        "comment": _("SLA breached - escalated to level {0}").format(level)}).insert(ignore_permissions=True)
        for u in target_list:
            notify(u, "Helpdesk", _("Escalated: {0}").format(t.subject), _("Level {0} SLA escalation").format(level),
                   f"/ess/hr/tickets/{name}", t.doctype, name)
    frappe.db.commit()
