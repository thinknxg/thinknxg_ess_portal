import frappe
from frappe import _
from frappe.utils import today, add_days, getdate, get_first_day
from thinknxg_ess_portal.api._guard import guard
from thinknxg_ess_portal.services import identity


def _team():
    guard(employee=False)
    team = identity.team_employees()
    if not team and not identity.is_hr():
        frappe.throw(_("The team workspace is for people managers."), frappe.PermissionError)
    return team


@frappe.whitelist(methods=["GET"])
def get_overview():
    team = _team()
    d = today()
    members = frappe.get_all("Employee", filters={"name": ["in", team or [""]]},
                             fields=["name", "employee_name", "designation", "department", "image", "reports_to"],
                             order_by="employee_name asc")
    ins = {}
    for c in frappe.get_all("Employee Checkin", filters={"employee": ["in", team or [""]], "time": [">=", d]},
                            fields=["employee", "log_type", "time"], order_by="time asc"):
        ins[c.employee] = c
    leave = {r.employee: r.leave_type for r in frappe.get_all(
        "Leave Application", filters={"employee": ["in", team or [""]], "docstatus": 1, "status": "Approved",
                                      "from_date": ["<=", d], "to_date": [">=", d]}, fields=["employee", "leave_type"])}
    for m in members:
        last = ins.get(m.name)
        m["today"] = ("On Leave" if m.name in leave else "Checked In" if last and last.log_type == "IN" else
                      "Checked Out" if last else "Not Checked In")
        m["leave_type"] = leave.get(m.name)
        m["first_seen"] = str(last.time)[11:16] if last else None
    counts = {}
    for m in members:
        counts[m["today"]] = counts.get(m["today"], 0) + 1
    upcoming = frappe.get_all("Leave Application", filters={"employee": ["in", team or [""]], "docstatus": 1,
                                                            "status": "Approved", "from_date": ["between", [add_days(d, 1), add_days(d, 14)]]},
                              fields=["employee_name", "leave_type", "from_date", "to_date"], order_by="from_date asc")
    return {"members": members, "counts": counts, "upcoming_leave": upcoming}


@frappe.whitelist(methods=["GET"])
def get_exceptions(days=7):
    team = _team()
    since = add_days(today(), -min(int(days or 7), 31))
    late = frappe.get_all("Attendance", filters={"employee": ["in", team or [""]], "docstatus": 1, "late_entry": 1,
                                                 "attendance_date": [">=", since]},
                          fields=["employee_name", "attendance_date", "in_time"], order_by="attendance_date desc")
    absent = frappe.db.sql("""select a.employee_name, a.attendance_date from `tabAttendance` a
        where a.employee in %(team)s and a.docstatus=1 and a.status='Absent' and a.attendance_date>=%(since)s
        order by a.attendance_date desc""", {"team": team or [""], "since": since}, as_dict=True)
    odd = frappe.db.sql("""select e.employee_name, date(c.time) d, count(*) n from `tabEmployee Checkin` c
        join `tabEmployee` e on e.name=c.employee where c.employee in %(team)s and c.time>=%(since)s and date(c.time)<%(today)s
        group by c.employee, date(c.time) having mod(count(*),2)=1""",
                        {"team": team or [""], "since": since, "today": today()}, as_dict=True)
    return {"late": late, "absent": absent, "missing_punch": odd}


@frappe.whitelist(methods=["GET"])
def get_member(employee):
    _team()
    identity.assert_team_member(employee)
    meta = frappe.get_meta("Employee")
    fields = [f for f in ("name", "employee_name", "designation", "department", "branch", "date_of_joining",
                          "image", "company_email", "cell_number", "reports_to") if f == "name" or meta.has_field(f)]
    data = frappe.db.get_value("Employee", employee, fields, as_dict=True)
    from thinknxg_ess_portal.api.leave import _balances
    try:
        data["balances"] = _balances(employee)
    except Exception:
        data["balances"] = []
    data["attendance"] = frappe.get_all("Attendance", filters={"employee": employee, "docstatus": 1,
                                                               "attendance_date": [">=", get_first_day(today())]},
                                        fields=["status", "count(name) as n"], group_by="status")
    if frappe.db.exists("DocType", "Goal"):
        data["goals"] = frappe.get_all("Goal", filters={"employee": employee, "is_group": 0},
                                       fields=["name", "goal_name", "progress", "status", "end_date"], limit=20)
    return data
