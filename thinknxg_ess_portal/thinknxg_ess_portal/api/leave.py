import frappe
from frappe import _
from frappe.utils import today, getdate, cint, flt, add_days, get_first_day, get_last_day
from thinknxg_ess_portal.api._guard import guard, page
from thinknxg_ess_portal.services import identity, hrms
from thinknxg_ess_portal.services.idempotency import run_once


def _balances(employee):
    details = hrms.leave_details(employee, today())
    out = []
    for lt, v in (details.get("leave_allocation") or {}).items():
        out.append({"leave_type": lt, "allocated": flt(v.get("total_leaves"), 2),
                    "taken": flt(v.get("leaves_taken"), 2), "pending": flt(v.get("leaves_pending_approval"), 2),
                    "expired": flt(v.get("expired_leaves"), 2), "remaining": flt(v.get("remaining_leaves"), 2)})
    return out


def _types(employee):
    details = hrms.leave_details(employee, today())
    types = list((details.get("leave_allocation") or {}).keys())
    for lwp in details.get("lwps") or []:
        if lwp not in types:
            types.append(lwp)
    return types


def _preview(emp, leave_type, from_date, to_date, half_day=0, half_day_date=None):
    fd, td = getdate(from_date), getdate(to_date)
    if fd > td:
        frappe.throw(_("From date cannot be after to date"))
    if leave_type not in _types(emp.name):
        frappe.throw(_("You have no allocation for {0}").format(leave_type))
    days = hrms.leave_days(emp.name, leave_type, fd, td, cint(half_day) or None, half_day_date)
    is_lwp = cint(frappe.db.get_value("Leave Type", leave_type, "is_lwp"))
    balance = None if is_lwp else hrms.leave_balance(emp.name, leave_type, fd, td)
    overlaps = frappe.db.sql("""select name, leave_type, from_date, to_date, status from `tabLeave Application`
        where employee=%s and docstatus<2 and status in ('Open','Approved') and to_date>=%s and from_date<=%s""",
                             (emp.name, fd, td), as_dict=True)
    holidays = [h for h in hrms.holidays_between(emp.name, fd, td)]
    approver = hrms.leave_approver(emp.name)
    return {"days": days, "is_lwp": bool(is_lwp), "balance": balance,
            "balance_after": None if balance is None else flt(balance - days, 2),
            "sufficient": True if balance is None else balance >= days, "overlaps": overlaps,
            "holidays": holidays, "approver": approver,
            "approver_name": frappe.utils.get_fullname(approver) if approver else None}


@frappe.whitelist(methods=["GET"])
def get_overview():
    emp = guard("enable_leave")
    upcoming = frappe.get_all("Leave Application", filters={"employee": emp.name, "docstatus": 1, "status": "Approved",
                                                            "to_date": [">=", today()]},
                              fields=["name", "leave_type", "from_date", "to_date", "total_leave_days"],
                              order_by="from_date asc", limit=5)
    approver = hrms.leave_approver(emp.name)
    return {"balances": _balances(emp.name), "types": _types(emp.name), "upcoming": upcoming,
            "recent": my_requests(limit=5),
            "approver": {"user": approver, "name": frappe.utils.get_fullname(approver)} if approver else None}


@frappe.whitelist(methods=["GET", "POST"])
def preview(leave_type, from_date, to_date, half_day=0, half_day_date=None):
    emp = guard("enable_leave")
    return _preview(emp, leave_type, from_date, to_date, half_day, half_day_date)


@frappe.whitelist(methods=["POST"])
def create_request(leave_type, from_date, to_date, half_day=0, half_day_date=None, reason=None,
                   client_request_id=None):
    emp = guard("enable_leave")

    def do():
        p = _preview(emp, leave_type, from_date, to_date, half_day, half_day_date)
        if p["overlaps"]:
            frappe.throw(_("These dates overlap with {0}").format(p["overlaps"][0].name))
        if not p["sufficient"]:
            allow_neg = cint(frappe.db.get_value("Leave Type", leave_type, "allow_negative"))
            if not allow_neg:
                frappe.throw(_("Insufficient balance: {0} day(s) requested, {1} available").format(
                    p["days"], p["balance"]))
        doc = frappe.get_doc({"doctype": "Leave Application", "employee": emp.name, "company": emp.company,
                              "leave_type": leave_type, "from_date": from_date, "to_date": to_date,
                              "half_day": cint(half_day), "half_day_date": half_day_date if cint(half_day) else None,
                              "description": (reason or "")[:1000], "leave_approver": p["approver"],
                              "status": "Open", "posting_date": today(), "follow_via_email": 1})
        doc.insert(ignore_permissions=True)
        return {"doctype": doc.doctype, "name": doc.name, "status": doc.status, "days": doc.total_leave_days}

    return run_once(client_request_id, "leave_request", do)


@frappe.whitelist(methods=["GET"])
def my_requests(status=None, limit=20, offset=0):
    emp = guard("enable_leave")
    limit, offset = page(limit, offset)
    flt_ = {"employee": emp.name}
    if status:
        flt_["status"] = status
    return frappe.get_all("Leave Application", filters=flt_, limit=limit, start=offset, order_by="creation desc",
                          fields=["name", "leave_type", "from_date", "to_date", "total_leave_days", "half_day",
                                  "status", "docstatus", "description", "leave_approver_name", "posting_date"])


@frappe.whitelist(methods=["POST"])
def withdraw_request(name, client_request_id=None):
    emp = guard("enable_leave")
    doc = frappe.get_doc("Leave Application", name)
    if doc.employee != emp.name:
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    if doc.docstatus != 0 or doc.status != "Open":
        frappe.throw(_("Only open requests can be withdrawn. Ask your manager to cancel approved leave."))
    frappe.delete_doc("Leave Application", name, ignore_permissions=True)
    return {"name": name, "withdrawn": True}


@frappe.whitelist(methods=["GET"])
def get_calendar(year=None, month=None, include_team=0):
    emp = guard("enable_leave")
    start = getdate(f"{cint(year) or getdate().year}-{cint(month) or getdate().month:02d}-01")
    end = get_last_day(start)
    events = []
    for r in frappe.get_all("Leave Application", filters={"employee": emp.name, "docstatus": ["<", 2],
                                                          "status": ["in", ["Open", "Approved"]],
                                                          "from_date": ["<=", end], "to_date": [">=", start]},
                            fields=["name", "leave_type", "from_date", "to_date", "status"]):
        events.append({"kind": "mine", "title": r.leave_type, "start": str(r.from_date), "end": str(r.to_date),
                       "status": r.status, "ref": r.name})
    for h in hrms.holidays_between(emp.name, start, end):
        events.append({"kind": "weekly_off" if h.weekly_off else "holiday", "title": h.description,
                       "start": str(h.holiday_date), "end": str(h.holiday_date)})
    if cint(include_team) and identity.is_manager():
        team = identity.team_employees()
        for r in frappe.get_all("Leave Application", filters={"employee": ["in", team], "docstatus": ["<", 2],
                                                              "status": ["in", ["Open", "Approved"]],
                                                              "from_date": ["<=", end], "to_date": [">=", start]},
                                fields=["employee_name", "leave_type", "from_date", "to_date", "status"]):
            events.append({"kind": "team", "title": f"{r.employee_name} · {r.leave_type}", "start": str(r.from_date),
                           "end": str(r.to_date), "status": r.status})
    return {"start": str(start), "end": str(end), "events": events}
