import frappe
from frappe.utils import cint

no_cache = 1


def get_context(context):
    context.no_cache = 1
    code = (frappe.form_dict.get("code") or "").strip().upper()[:20]
    context.code = code
    context.checked = bool(code)
    context.result = None
    if not cint(frappe.db.get_single_value("ESS Portal Settings", "public_verification")):
        context.disabled = True
        return context
    if code:
        ip = getattr(frappe.local, "request_ip", "x")
        key = f"ess_verify:{ip}"
        n = frappe.cache.incrby(key, 1)
        if n == 1:
            frappe.cache.expire(key, 3600)
        if n > 30:
            context.rate_limited = True
            return context
        row = frappe.db.get_value("ESS Document Request", {"verification_code": code, "status": "Generated"},
                                  ["template", "employee_name", "generated_on"], as_dict=True)
        if row:
            context.result = {"document": row.template, "issued_on": frappe.utils.formatdate(row.generated_on),
                              "employee_name": row.employee_name}
    return context
