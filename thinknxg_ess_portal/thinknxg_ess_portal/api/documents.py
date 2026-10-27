import frappe
from frappe import _
from frappe.utils import cint
from thinknxg_ess_portal.api._guard import guard
from thinknxg_ess_portal.services import identity, documents
from thinknxg_ess_portal.services.idempotency import run_once
from thinknxg_ess_portal.services.ratelimit import check_rate
from thinknxg_ess_portal.services.audit import log_event


@frappe.whitelist(methods=["GET"])
def overview():
    emp = guard("enable_documents")
    templates = []
    for t in frappe.get_all("ESS Document Template", filters={"is_active": 1, "visible_to_employees": 1},
                            fields=["name", "document_type", "description", "requires_approval", "requires_purpose",
                                    "addressee_required"]):
        t["blocked_reasons"] = documents.eligibility(t.name, emp.name)
        templates.append(t)
    requests = frappe.get_all("ESS Document Request", filters={"employee": emp.name},
                              fields=["name", "template", "status", "purpose", "creation", "generated_on",
                                      "rejection_reason", "verification_code"], order_by="creation desc", limit=50)
    from thinknxg_ess_portal.api.policies import list_mine
    return {"templates": templates, "requests": requests, "policies": list_mine()}


@frappe.whitelist(methods=["POST"])
def request(template, purpose=None, addressed_to=None, language="en", client_request_id=None):
    guard("enable_documents")
    check_rate("document", identity.settings().get("document_rate_limit_per_day") or 5, seconds=86400)
    return run_once(client_request_id, "document_request",
                    lambda: documents.create_request(template, purpose, addressed_to, language))


@frappe.whitelist(methods=["POST"])
def cancel_request(name):
    emp = guard("enable_documents")
    doc = frappe.get_doc("ESS Document Request", name)
    if doc.employee != emp.name or doc.status not in ("Requested", "Pending Approval"):
        frappe.throw(_("This request cannot be cancelled"))
    doc.db_set("status", "Cancelled")
    return {"name": name, "status": "Cancelled"}


@frappe.whitelist(methods=["GET"])
def download(name):
    guard("enable_documents", employee=False)
    doc = frappe.get_doc("ESS Document Request", name)
    me = identity.get_employee(required=False)
    own = me and doc.employee == me.name
    if not (own or identity.is_hr()):
        frappe.throw(_("Not found"), frappe.DoesNotExistError)
    if doc.status != "Generated" or not doc.output_file:
        frappe.throw(_("Document is not ready yet"))
    f = frappe.get_doc("File", {"file_url": doc.output_file, "attached_to_name": doc.name})
    log_event("Download", doc.doctype, doc.name, employee=doc.employee,
              details="own document" if own else "HR download")
    frappe.local.response.filename = f"{doc.template}-{doc.name}.pdf".replace(" ", "_")
    frappe.local.response.filecontent = f.get_content()
    frappe.local.response.type = "pdf"


# ------------------------------------------------------------------ HR administration
def _hr():
    guard("enable_documents", employee=False)
    if not identity.is_hr():
        frappe.throw(_("Not permitted"), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def admin_requests(status=None, limit=100):
    _hr()
    flt = {}
    if status:
        flt["status"] = status
    scope = identity.hr_scope_employees()
    if scope is not None:
        flt["employee"] = ["in", scope or [""]]
    rows = frappe.get_all("ESS Document Request", filters=flt, limit=min(cint(limit) or 100, 500),
                          fields=["name", "employee", "employee_name", "template", "template_version", "status",
                                  "purpose", "creation", "approved_by", "generated_on", "verification_code"],
                          order_by="creation desc")
    templates = frappe.get_all("ESS Document Template", fields=["name", "document_type", "is_active", "version",
                                                                "requires_approval", "include_salary", "modified"])
    return {"requests": rows, "templates": templates}


@frappe.whitelist(methods=["POST"])
def regenerate(name):
    _hr()
    doc = frappe.get_doc("ESS Document Request", name)
    if doc.status not in ("Generated", "Approved"):
        frappe.throw(_("Only approved or generated requests can be regenerated"))
    doc.db_set("status", "Approved")
    frappe.enqueue("thinknxg_ess_portal.services.documents.generate", request=name, queue="short",
                   enqueue_after_commit=True)
    log_event("Document Generated", doc.doctype, name, employee=doc.employee, details="regenerate requested")
    return {"name": name, "status": "Approved"}
