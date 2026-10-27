import frappe
from frappe import _
from frappe.utils import now_datetime
from thinknxg_ess_portal.services.identity import settings

NEVER_EDITABLE = {"name", "user_id", "company", "department", "designation", "reports_to", "status",
                  "date_of_joining", "ctc", "salary_mode", "employee", "holiday_list", "leave_approver",
                  "expense_approver", "relieving_date"}


def editable_fields():
    raw = settings().get("profile_editable_fields") or ""
    meta = frappe.get_meta("Employee")
    fields = {f.strip() for f in raw.split(",") if f.strip()}
    return {f for f in fields if f not in NEVER_EDITABLE and meta.has_field(f)}


def field_labels():
    meta = frappe.get_meta("Employee")
    return {f: meta.get_label(f) for f in editable_fields()}


def apply(request_name):
    req = frappe.get_doc("ESS Profile Change Request", request_name)
    if req.status != "Pending":
        frappe.throw(_("Only pending requests can be approved"))
    allowed = editable_fields()
    emp = frappe.get_doc("Employee", req.employee)
    for row in req.items:
        if row.field_name not in allowed:
            frappe.throw(_("Field {0} is not editable").format(row.field_name))
        emp.set(row.field_name, row.new_value)
    emp.flags.ignore_permissions = True
    emp.save()
    req.db_set({"status": "Approved", "reviewed_by": frappe.session.user, "reviewed_on": now_datetime()})
    from thinknxg_ess_portal.services.audit import log_event
    log_event("Profile Change", req.doctype, req.name, employee=req.employee,
              details="Applied: " + ", ".join(r.field_name for r in req.items))
