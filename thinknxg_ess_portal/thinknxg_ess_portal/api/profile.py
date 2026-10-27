import frappe
from frappe import _
from frappe.utils import getdate
from thinknxg_ess_portal.api._guard import guard, parse
from thinknxg_ess_portal.services.idempotency import run_once
from thinknxg_ess_portal.services.profile import editable_fields, field_labels

VIEW_FIELDS = ["name", "employee_name", "first_name", "last_name", "gender", "date_of_birth", "date_of_joining",
               "designation", "department", "branch", "company", "reports_to", "employment_type", "image",
               "company_email", "personal_email", "cell_number", "current_address", "permanent_address",
               "person_to_be_contacted", "emergency_phone_number", "relation", "marital_status", "nationality"]
MASKED = {"bank_ac_no", "iban"}


def _mask(v):
    v = str(v or "")
    return ("•" * max(len(v) - 4, 0) + v[-4:]) if v else ""


@frappe.whitelist(methods=["GET"])
def get_profile():
    emp = guard()
    meta = frappe.get_meta("Employee")
    fields = [f for f in VIEW_FIELDS if f == "name" or meta.has_field(f)]
    data = frappe.db.get_value("Employee", emp.name, fields, as_dict=True)
    if data.reports_to:
        data["reports_to_name"] = frappe.db.get_value("Employee", data.reports_to, "employee_name")
    editable = []
    for f, label in field_labels().items():
        val = frappe.db.get_value("Employee", emp.name, f)
        df = meta.get_field(f)
        editable.append({"field": f, "label": label, "value": _mask(val) if f in MASKED else val,
                         "fieldtype": df.fieldtype, "options": df.options if df.fieldtype == "Select" else None,
                         "sensitive": f in MASKED or f == "bank_name"})
    return {
        "profile": data, "editable": editable,
        "change_requests": frappe.get_all("ESS Profile Change Request", filters={"employee": emp.name},
                                          fields=["name", "status", "creation", "review_comment"],
                                          order_by="creation desc", limit=10),
        "documents": frappe.get_all("ESS Employee Document", filters={"employee": emp.name},
                                    fields=["name", "document_type", "document_number", "issue_date", "expiry_date",
                                            "verified", "attachment"], order_by="expiry_date asc"),
        "badges": frappe.db.sql("""select a.badge, a.awarded_on, b.icon, b.color, b.description from `tabESS Badge Award` a
                join `tabESS Badge` b on b.name=a.badge where a.employee=%s order by a.awarded_on desc""", emp.name,
                                as_dict=True),
    }


@frappe.whitelist(methods=["POST"])
def request_change(changes, reason=None, attachment=None, client_request_id=None):
    emp = guard()
    changes = parse(changes, {})
    allowed = editable_fields()
    labels = field_labels()
    items = []
    for field, value in changes.items():
        if field not in allowed:
            frappe.throw(_("{0} cannot be changed here").format(field))
        old = frappe.db.get_value("Employee", emp.name, field)
        if str(old or "") == str(value or ""):
            continue
        items.append({"field_name": field, "field_label": labels.get(field, field),
                      "old_value": _mask(old) if field in MASKED else old, "new_value": str(value or "")[:500]})
    if not items:
        frappe.throw(_("No changes to submit"))
    if frappe.db.exists("ESS Profile Change Request", {"employee": emp.name, "status": "Pending"}):
        frappe.throw(_("You already have a pending profile update. Please wait for HR to review it."))

    def do():
        doc = frappe.get_doc({"doctype": "ESS Profile Change Request", "employee": emp.name, "status": "Pending",
                              "reason": (reason or "")[:500], "attachment": attachment, "items": items})
        doc.insert(ignore_permissions=True)
        return {"doctype": doc.doctype, "name": doc.name}

    return run_once(client_request_id, "profile_change", do)


@frappe.whitelist(methods=["POST"])
def save_employee_document(document_type, expiry_date=None, document_number=None, issue_date=None,
                           issuing_authority=None, attachment=None, name=None, client_request_id=None):
    emp = guard()
    if attachment and not frappe.db.exists("File", {"file_url": attachment, "owner": frappe.session.user}):
        frappe.throw(_("Attachment not found"))

    def do():
        if name:
            doc = frappe.get_doc("ESS Employee Document", name)
            if doc.employee != emp.name:
                frappe.throw(_("Not permitted"), frappe.PermissionError)
        else:
            doc = frappe.new_doc("ESS Employee Document")
            doc.employee = emp.name
        doc.update({"document_type": document_type, "document_number": (document_number or "")[:60],
                    "issue_date": issue_date or None, "expiry_date": expiry_date or None,
                    "issuing_authority": issuing_authority, "verified": 0, "reminder_sent_on": None})
        if attachment:
            doc.attachment = attachment
        doc.save(ignore_permissions=True)
        if attachment:
            f = frappe.db.get_value("File", {"file_url": attachment}, "name")
            frappe.db.set_value("File", f, {"attached_to_doctype": doc.doctype, "attached_to_name": doc.name,
                                            "is_private": 1})
        return {"doctype": doc.doctype, "name": doc.name}

    return run_once(client_request_id, "employee_document", do)
