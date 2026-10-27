import frappe
from frappe import _
from thinknxg_ess_portal.api._guard import guard
from thinknxg_ess_portal.services import identity, analytics


@frappe.whitelist(methods=["GET"])
def employee():
    emp = guard("enable_analytics")
    return analytics.employee(emp.name)


@frappe.whitelist(methods=["GET"])
def manager():
    guard("enable_analytics", employee=False)
    if not identity.is_manager():
        frappe.throw(_("Team analytics are for people managers."), frappe.PermissionError)
    return analytics.manager(frappe.session.user)


@frappe.whitelist(methods=["GET"])
def hr():
    guard("enable_analytics", employee=False)
    if not identity.is_hr():
        frappe.throw(_("HR analytics are restricted to HR."), frappe.PermissionError)
    return analytics.hr(frappe.session.user)
