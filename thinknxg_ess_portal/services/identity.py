"""Authenticated user -> Employee -> authorised data scope.

Nothing in here trusts client input: every scope is derived from frappe.session.user.
"""
import frappe
from frappe import _

HR_ROLES = {"HR Manager", "HR User"}
ADMIN_ROLES = {"System Manager", "ESS Portal Admin"}
EMP_FIELDS = ["name", "employee_name", "first_name", "user_id", "company", "department", "designation",
              "branch", "reports_to", "date_of_joining", "holiday_list", "image", "status", "gender",
              "employment_type", "default_shift", "leave_approver", "expense_approver", "date_of_birth"]


def settings():
    data = frappe.cache.get_value("ess_portal_settings")
    if data is None:
        doc = frappe.get_cached_doc("ESS Portal Settings")
        data = {k: v for k, v in doc.as_dict().items()
                if not k.startswith("_") and k not in ("ai_api_key", "vapid_private_key")}
        frappe.cache.set_value("ess_portal_settings", data, expires_in_sec=300)
    return frappe._dict(data)


def require_login():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)


def require_module(flag):
    if not settings().get(flag):
        frappe.throw(_("This module is disabled by your administrator."), frappe.PermissionError)


def roles(user=None):
    return set(frappe.get_roles(user or frappe.session.user))


def is_admin(user=None):
    return bool(roles(user) & ADMIN_ROLES) or (user or frappe.session.user) == "Administrator"


def is_hr(user=None):
    return bool(roles(user) & HR_ROLES) or is_admin(user)


def is_hr_manager(user=None):
    return "HR Manager" in roles(user) or is_admin(user)


def is_payroll_officer(user=None):
    return "ESS Payroll Officer" in roles(user)


def is_agent(user=None):
    r = roles(user)
    return bool(r & {"ESS HR Agent", "ESS Payroll Officer", "HR Manager"}) or is_admin(user)


def get_employee(user=None, required=True):
    user = user or frappe.session.user
    cache = _local_cache("ess_employee_cache")
    if user not in cache:
        meta = frappe.get_meta("Employee")
        fields = [f for f in EMP_FIELDS if f == "name" or meta.has_field(f)]
        cache[user] = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, fields, as_dict=True)
    emp = cache[user]
    if not emp and required:
        frappe.throw(_("No active employee profile is linked to your account. Please contact HR."),
                     frappe.PermissionError)
    return emp


def team_employees(user=None, recursive=True):
    """Employees the user manages: reporting line (recursive) + departments they head."""
    user = user or frappe.session.user
    cache = _local_cache("ess_team_cache")
    key = (user, recursive)
    if key in cache:
        return cache[key]
    me = get_employee(user, required=False)
    team = set()
    if me:
        frontier = [me.name]
        while frontier:
            rows = frappe.get_all("Employee", filters={"reports_to": ["in", frontier], "status": "Active"},
                                  pluck="name")
            rows = [r for r in rows if r not in team and r != me.name]
            team.update(rows)
            frontier = rows if recursive else []
    if frappe.get_meta("Department").has_field("ess_department_head"):
        heads = frappe.get_all("Department", filters={"ess_department_head": user}, fields=["lft", "rgt"])
        for d in heads:
            depts = frappe.get_all("Department", filters={"lft": [">=", d.lft], "rgt": ["<=", d.rgt]}, pluck="name")
            team.update(frappe.get_all("Employee", filters={"department": ["in", depts], "status": "Active"},
                                       pluck="name"))
    if me:
        team.discard(me.name)
    cache[key] = sorted(team)
    return cache[key]


def is_manager(user=None):
    return bool(team_employees(user))


def assert_team_member(employee, user=None):
    if employee not in team_employees(user) and not is_hr(user):
        frappe.throw(_("You are not authorised to view this employee."), frappe.PermissionError)


def hr_scope_employees(user=None):
    """HR users see their company (or all if HR Manager/admin). Returns None for unrestricted."""
    if is_hr_manager(user):
        return None
    me = get_employee(user, required=False)
    if is_hr(user) and me:
        return frappe.get_all("Employee", filters={"company": me.company, "status": "Active"}, pluck="name")
    return team_employees(user)


def capabilities(user=None):
    s = settings()
    mgr = is_manager(user)
    emp = get_employee(user, required=False)
    return {
        "employee": bool(emp),
        "manager": mgr,
        "hr": is_hr(user),
        "hr_manager": is_hr_manager(user),
        "agent": is_agent(user),
        "payroll_officer": is_payroll_officer(user),
        "admin": is_admin(user),
        "modules": {k.replace("enable_", ""): bool(s.get(k)) for k in s if k.startswith("enable_")},
    }


def has_app_permission():
    return frappe.session.user != "Guest"


def _local_cache(key):
    """Per-request cache on frappe.local (v16's local has no __dict__)."""
    cache = getattr(frappe.local, key, None)
    if cache is None:
        cache = {}
        setattr(frappe.local, key, cache)
    return cache
