"""Record-level rules for custom ESS DocTypes (desk + REST).

Portal APIs additionally enforce scope in services; these hooks make sure the generic
/api/resource endpoints and Desk list views can never widen what a user sees.
"""
import frappe

FULL = {"System Manager", "ESS Portal Admin", "HR Manager"}


def _roles(user):
    return set(frappe.get_roles(user))


def _full(user):
    return bool(_roles(user) & FULL) or user == "Administrator"


def _employees(user):
    return [e for e in frappe.get_all("Employee", filters={"user_id": user}, pluck="name")]


def _esc(v):
    return frappe.db.escape(v)


def _in(values):
    return "(" + ",".join(_esc(v) for v in values) + ")" if values else "('')"


# ---- tickets
def ticket_query(user=None):
    user = user or frappe.session.user
    if _full(user):
        return ""
    roles = _roles(user)
    mine = f"(`tabESS HR Ticket`.raised_by={_esc(user)} or `tabESS HR Ticket`.employee in {_in(_employees(user))})"
    if "ESS Payroll Officer" in roles:
        return f"(`tabESS HR Ticket`.assigned_to={_esc(user)} or `tabESS HR Ticket`.is_confidential=1 or {mine})"
    if "ESS HR Agent" in roles:
        return (f"((`tabESS HR Ticket`.is_confidential=0) or `tabESS HR Ticket`.assigned_to={_esc(user)} "
                f"or {mine})")
    return mine


def ticket_has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if _full(user):
        return True
    roles = _roles(user)
    owner = doc.raised_by == user or doc.employee in _employees(user)
    if owner:
        return ptype in (None, "read", "print", "email")
    if doc.assigned_to == user:
        return True
    if "ESS Payroll Officer" in roles:
        return True
    if "ESS HR Agent" in roles and not doc.is_confidential:
        return True
    return False


def ticket_comment_query(user=None):
    user = user or frappe.session.user
    if _full(user):
        return ""
    cond = ticket_query(user).replace("`tabESS HR Ticket`.", "t.")
    roles = _roles(user)
    internal = "" if roles & {"ESS HR Agent", "ESS Payroll Officer"} else " and `tabESS HR Ticket Comment`.is_internal=0"
    return (f"(`tabESS HR Ticket Comment`.ticket in (select t.name from `tabESS HR Ticket` t where {cond}){internal})")


def ticket_comment_has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if _full(user):
        return True
    ticket = frappe.get_cached_doc("ESS HR Ticket", doc.ticket)
    if not ticket_has_permission(ticket, "read", user):
        return False
    is_staff = bool(_roles(user) & {"ESS HR Agent", "ESS Payroll Officer"})
    if doc.is_internal and not is_staff:
        return False
    return ptype in (None, "read", "print") or is_staff


# ---- generic "belongs to my employee record"
def _employee_scoped_query(dt, user, extra_roles=()):
    if _full(user) or (_roles(user) & set(extra_roles)):
        return ""
    return f"`tab{dt}`.employee in {_in(_employees(user))}"


def _employee_scoped(doc, ptype, user, extra_roles=()):
    if _full(user) or (_roles(user) & set(extra_roles)):
        return True
    return doc.employee in _employees(user) and ptype in (None, "read", "print")


def document_request_query(user=None):
    return _employee_scoped_query("ESS Document Request", user or frappe.session.user, ("HR User",))


def document_request_has_permission(doc, ptype=None, user=None):
    return _employee_scoped(doc, ptype, user or frappe.session.user, ("HR User",))


def employee_document_query(user=None):
    return _employee_scoped_query("ESS Employee Document", user or frappe.session.user, ("HR User",))


def employee_document_has_permission(doc, ptype=None, user=None):
    return _employee_scoped(doc, ptype, user or frappe.session.user, ("HR User",))


def profile_change_query(user=None):
    return _employee_scoped_query("ESS Profile Change Request", user or frappe.session.user, ("HR User",))


def profile_change_has_permission(doc, ptype=None, user=None):
    return _employee_scoped(doc, ptype, user or frappe.session.user, ("HR User",))


def policy_ack_query(user=None):
    return _employee_scoped_query("ESS Policy Acknowledgement", user or frappe.session.user, ("HR User",))


def policy_ack_has_permission(doc, ptype=None, user=None):
    return _employee_scoped(doc, ptype, user or frappe.session.user, ("HR User",))


def badge_award_query(user=None):
    return ""  # badges are public achievements


def badge_award_has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    return _full(user) or ptype in (None, "read")


# ---- recognition visibility
def recognition_query(user=None):
    user = user or frappe.session.user
    if _full(user):
        return ""
    t = "`tabESS Recognition`"
    return (f"({t}.sender={_esc(user)} or {t}.recipient_user={_esc(user)} or "
            f"({t}.status='Approved' and {t}.visibility='Public'))")


def recognition_has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if _full(user):
        return True
    if ptype not in (None, "read"):
        return False
    return doc.sender == user or doc.recipient_user == user or (
        doc.status == "Approved" and doc.visibility == "Public")


# ---- user-owned rows
def own_user_query(user=None):
    user = user or frappe.session.user
    if _full(user):
        return ""
    return f"`user`={_esc(user)}"


def own_user_has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    return _full(user) or doc.get("user") == user


def delegation_query(user=None):
    user = user or frappe.session.user
    if _full(user):
        return ""
    t = "`tabESS Approval Delegation`"
    return f"({t}.delegator={_esc(user)} or {t}.delegate={_esc(user)})"


def delegation_has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if _full(user):
        return True
    if doc.delegator == user:
        return True
    return doc.delegate == user and ptype in (None, "read")
