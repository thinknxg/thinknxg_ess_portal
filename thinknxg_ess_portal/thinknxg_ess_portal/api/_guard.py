import json
import frappe
from frappe import _
from thinknxg_ess_portal.services import identity


def guard(module=None, employee=True):
    identity.require_login()
    if module:
        identity.require_module(module)
    return identity.get_employee() if employee else identity.get_employee(required=False)


def parse(value, default=None):
    if value in (None, ""):
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        frappe.throw(_("Invalid JSON payload"))


def page(limit, offset):
    return max(1, min(frappe.utils.cint(limit) or 20, 100)), max(frappe.utils.cint(offset), 0)
