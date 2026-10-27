import frappe
from frappe import _
from frappe.utils import (now_datetime, today, add_months, getdate, month_diff, get_first_day, get_url, cint)
from thinknxg_ess_portal.services import identity
from thinknxg_ess_portal.services.audit import log_event
from thinknxg_ess_portal.services.notifications import notify

SAFE_EMPLOYEE_FIELDS = ["name", "employee_name", "salutation", "first_name", "last_name", "gender", "designation",
                        "department", "branch", "date_of_joining", "employment_type", "company", "status",
                        "relieving_date", "nationality" ]


def eligibility(template, employee):
    """Return list of human-readable reasons the employee cannot request this template."""
    reasons = []
    t = frappe.get_cached_doc("ESS Document Template", template)
    if not t.is_active or not t.visible_to_employees:
        return [_("This document is not available.")]
    statuses = {s.strip() for s in (t.employee_statuses or "Active").split(",") if s.strip()}
    emp = frappe.db.get_value("Employee", employee, ["status", "date_of_joining"], as_dict=True)
    if emp.status not in statuses:
        reasons.append(_("Not available for your employment status."))
    if t.min_service_months and emp.date_of_joining:
        if month_diff(today(), emp.date_of_joining) - 1 < t.min_service_months:
            reasons.append(_("Requires at least {0} months of service.").format(t.min_service_months))
    if t.max_per_month:
        count = frappe.db.count("ESS Document Request", {
            "employee": employee, "template": template, "status": ["not in", ["Rejected", "Cancelled"]],
            "creation": [">=", get_first_day(today())]})
        if count >= t.max_per_month:
            reasons.append(_("Monthly limit of {0} reached for this document.").format(t.max_per_month))
    return reasons


def create_request(template, purpose=None, addressed_to=None, language="en"):
    emp = identity.get_employee()
    t = frappe.get_cached_doc("ESS Document Template", template)
    problems = eligibility(template, emp.name)
    if problems:
        frappe.throw("<br>".join(problems))
    if t.requires_purpose and not (purpose or "").strip():
        frappe.throw(_("Please state the purpose of this document."))
    if t.addressee_required and not (addressed_to or "").strip():
        frappe.throw(_("Please state who the document is addressed to."))
    req = frappe.get_doc({"doctype": "ESS Document Request", "employee": emp.name, "template": template,
                          "purpose": (purpose or "")[:500], "addressed_to": (addressed_to or "")[:140],
                          "language": language if language in ("en", "ar") else "en",
                          "status": "Pending Approval" if t.requires_approval else "Approved"})
    req.insert(ignore_permissions=True)
    if t.requires_approval:
        approvers = frappe.get_all("Has Role", filters={"role": t.approver_role or "HR Manager",
                                                        "parenttype": "User"}, pluck="parent", limit=20)
        for u in approvers:
            if u not in ("Administrator", "Guest"):
                notify(u, "Approvals", _("Document request: {0}").format(template), emp.employee_name,
                       "/ess/team/approvals", req.doctype, req.name)
    else:
        frappe.enqueue("thinknxg_ess_portal.services.documents.generate", request=req.name, queue="short",
                       enqueue_after_commit=True)
    return {"doctype": req.doctype, "name": req.name, "status": req.status}


def review(doc, approved, comment=None):
    if doc.status != "Pending Approval":
        frappe.throw(_("Request is not pending approval"))
    if approved:
        doc.db_set({"status": "Approved", "approved_by": frappe.session.user, "approved_on": now_datetime()})
        frappe.enqueue("thinknxg_ess_portal.services.documents.generate", request=doc.name, queue="short",
                       enqueue_after_commit=True)
    else:
        doc.db_set({"status": "Rejected", "rejection_reason": comment, "approved_by": frappe.session.user,
                    "approved_on": now_datetime()})
        notify(frappe.db.get_value("Employee", doc.employee, "user_id"), "Documents",
               _("Document request rejected"), comment or "", "/ess/documents", doc.doctype, doc.name)


def _salary(employee):
    slip = frappe.get_all("Salary Slip", filters={"employee": employee, "docstatus": 1},
                          fields=["name", "gross_pay", "net_pay", "currency", "start_date", "end_date"],
                          order_by="end_date desc", limit=1)
    return slip[0] if slip else None


def build_context(req, template):
    emp = frappe.db.get_value("Employee", req.employee,
                              [f for f in SAFE_EMPLOYEE_FIELDS if frappe.get_meta("Employee").has_field(f)
                               or f == "name"], as_dict=True)
    company = frappe.db.get_value("Company", emp.company, ["company_name", "country", "default_currency"],
                                  as_dict=True)
    code = req.verification_code or frappe.generate_hash(length=12).upper()
    verify = get_url(f"/ess-verify?code={code}") if cint(identity.settings().get("public_verification")) else None
    return {
        "employee": emp, "company": company, "today": today(), "purpose": req.purpose,
        "addressed_to": req.addressed_to, "language": req.language,
        "salary": _salary(req.employee) if template.include_salary else None,
        "signatory": {"name": template.signatory_name, "designation": template.signatory_designation,
                      "signature": template.signature_image},
        "verification_code": code, "verify_url": verify,
    }


def generate(request):
    """Background job: render the approved server-side template to a private PDF."""
    req = frappe.get_doc("ESS Document Request", request)
    if req.status not in ("Approved",):
        return
    t = frappe.get_doc("ESS Document Template", req.template)
    ctx = build_context(req, t)
    body = frappe.render_template(t.template_html, ctx)
    header = frappe.db.get_value("Letter Head", t.letter_head, "content") if t.letter_head else ""
    html = f"""<!DOCTYPE html><html dir="{'rtl' if req.language == 'ar' else 'ltr'}"><head><meta charset="utf-8">
<style>body{{font-family:Inter,'Noto Sans Arabic',Arial,sans-serif;}}</style></head>
<body>{header or ''}{body}</body></html>"""
    from frappe.utils.pdf import get_pdf
    pdf = get_pdf(html)
    f = frappe.get_doc({"doctype": "File", "file_name": f"{req.name}.pdf", "is_private": 1, "content": pdf,
                        "attached_to_doctype": req.doctype, "attached_to_name": req.name,
                        "attached_to_field": "output_file"}).insert(ignore_permissions=True)
    req.db_set({"status": "Generated", "output_file": f.file_url, "generated_on": now_datetime(),
                "verification_code": ctx["verification_code"], "template_version": t.version})
    log_event("Document Generated", req.doctype, req.name, employee=req.employee,
              details=f"template={t.name} v{t.version}", user=frappe.db.get_value("Employee", req.employee, "user_id"))
    notify(frappe.db.get_value("Employee", req.employee, "user_id"), "Documents", _("Your document is ready"),
           t.template_name, "/ess/documents", req.doctype, req.name)
    frappe.db.commit()
