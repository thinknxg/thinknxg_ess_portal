"""Every mutation from the portal carries a client_request_id (UUID) so retries,
double taps and queued offline submissions never create duplicates."""
import frappe
from frappe import _
from frappe.utils import now_datetime


def run_once(client_request_id, action_type, fn):
    if not client_request_id:
        return fn()
    cid = str(client_request_id)[:140]
    existing = frappe.db.get_value("ESS Offline Action", {"client_request_id": cid},
                                   ["name", "user", "status", "reference_doctype", "reference_name"], as_dict=True)
    if existing:
        if existing.user != frappe.session.user:
            frappe.throw(_("Invalid request id"), frappe.PermissionError)
        if existing.status == "Processed":
            return {"duplicate": True, "doctype": existing.reference_doctype, "name": existing.reference_name}
        frappe.throw(_("This request is already being processed."))
    rec = frappe.get_doc({"doctype": "ESS Offline Action", "user": frappe.session.user,
                          "client_request_id": cid, "action_type": action_type, "status": "Received",
                          "received_on": now_datetime()}).insert(ignore_permissions=True)
    result = fn()
    if isinstance(result, dict):
        rec.db_set({"status": "Processed", "reference_doctype": result.get("doctype"),
                    "reference_name": result.get("name")}, update_modified=False)
    else:
        rec.db_set("status", "Processed", update_modified=False)
    return result
