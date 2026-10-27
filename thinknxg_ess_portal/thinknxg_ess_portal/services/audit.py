import frappe


def log_event(event_type, reference_doctype=None, reference_name=None, employee=None, details=None, user=None):
    """Append-only audit trail. Never raises into the caller."""
    try:
        frappe.get_doc({
            "doctype": "ESS Audit Event", "event_type": event_type,
            "user": user or frappe.session.user, "employee": employee,
            "reference_doctype": reference_doctype, "reference_name": reference_name,
            "details": (details or "")[:1000],
            "ip_address": getattr(frappe.local, "request_ip", None),
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(title="ESS audit write failed")
