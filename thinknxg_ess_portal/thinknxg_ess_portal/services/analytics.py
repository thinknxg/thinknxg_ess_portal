"""Server-side, scope-filtered aggregates. No raw employee rows are returned to the browser."""
import frappe
from frappe.utils import today, add_months, get_first_day, add_days, getdate, flt, cint
from thinknxg_ess_portal.services import identity


def min_group():
    return max(cint(identity.settings().get("min_group_size")) or 5, 3)


def suppress(rows, count_key="n"):
    """Hide buckets that would identify fewer than `min_group` people."""
    k = min_group()
    return [r if (r.get(count_key) or 0) >= k else {**r, count_key: None, "suppressed": True} for r in rows]


def _months(n=6):
    start = get_first_day(add_months(today(), -(n - 1)))
    return start, [str(add_months(start, i))[:7] for i in range(n)]


def employee(emp):
    start, months = _months(6)
    att = frappe.db.sql("""select date_format(attendance_date,'%%Y-%%m') m, status, count(*) n,
               sum(late_entry) late from `tabAttendance` where employee=%s and docstatus=1 and attendance_date>=%s
               group by m, status""", (emp, start), as_dict=True)
    series = {m: {"Present": 0, "Absent": 0, "On Leave": 0, "Half Day": 0, "Work From Home": 0, "late": 0}
              for m in months}
    for r in att:
        if r.m in series:
            series[r.m][r.status] = r.n
            series[r.m]["late"] += cint(r.late)
    leave = frappe.db.sql("""select leave_type, sum(total_leave_days) days from `tabLeave Application`
               where employee=%s and docstatus=1 and status='Approved' and from_date>=%s group by leave_type""",
                          (emp, get_first_day(add_months(today(), -11))), as_dict=True)
    turnaround = frappe.db.sql("""select avg(timestampdiff(HOUR, creation, modified)) h from `tabLeave Application`
               where employee=%s and docstatus=1 and creation>=%s""", (emp, start))[0][0]
    return {"attendance": [{"month": m, **v} for m, v in series.items()],
            "leave_usage": leave, "avg_leave_turnaround_hours": flt(turnaround, 1)}


def manager(user):
    team = identity.team_employees(user)
    if not team:
        return {"team_size": 0}
    d = today()
    on_leave = frappe.db.count("Leave Application", {"employee": ["in", team], "docstatus": 1, "status": "Approved",
                                                       "from_date": ["<=", d], "to_date": [">=", d]})
    present = frappe.db.count("Employee Checkin", {"employee": ["in", team], "time": [">=", d], "log_type": "IN"})
    start, months = _months(6)
    late = frappe.db.sql("""select date_format(attendance_date,'%%Y-%%m') m, sum(late_entry) late,
            sum(status='Absent') absent, count(*) n from `tabAttendance`
            where employee in %(team)s and docstatus=1 and attendance_date>=%(start)s group by m""",
                         {"team": team, "start": start}, as_dict=True)
    by_m = {r.m: r for r in late}
    from thinknxg_ess_portal.services.workflow import pending
    pend = pending(user)
    age = {"0-1d": 0, "2-3d": 0, "4-7d": 0, ">7d": 0}
    for p in pend:
        a = p["age_days"]
        age["0-1d" if a <= 1 else "2-3d" if a <= 3 else "4-7d" if a <= 7 else ">7d"] += 1
    goals = {}
    if frappe.db.exists("DocType", "Goal"):
        for r in frappe.get_all("Goal", filters={"employee": ["in", team], "is_group": 0},
                                fields=["status", "count(name) as n"], group_by="status"):
            goals[r.status or "Pending"] = r.n
    overtime = []
    if frappe.db.exists("DocType", "Overtime Slip"):
        meta = frappe.get_meta("Overtime Slip")
        dur = "total_overtime_duration" if meta.has_field("total_overtime_duration") else None
        if dur:
            overtime = frappe.db.sql(f"""select date_format(posting_date,'%%Y-%%m') m, sum({dur})/3600 hours
                from `tabOvertime Slip` where employee in %(team)s and docstatus=1 and posting_date>=%(start)s
                group by m""", {"team": team, "start": start}, as_dict=True)
    return {
        "team_size": len(team), "on_leave_today": on_leave, "checked_in_today": present,
        "not_checked_in": max(len(team) - present - on_leave, 0),
        "pending_approvals": len(pend), "approval_age": age,
        "trend": [{"month": m, "late": cint(by_m[m].late) if m in by_m else 0,
                   "absent": cint(by_m[m].absent) if m in by_m else 0} for m in months],
        "goals": goals, "overtime": overtime,
        "suppressed": len(team) < min_group(),
    }


def hr(user):
    scope = identity.hr_scope_employees(user)
    emp_filter = "" if scope is None else "and employee in %(scope)s"
    params = {"scope": scope or [""], "since": add_days(today(), -90)}
    tickets = frappe.db.sql(f"""select status, count(*) n from `tabESS HR Ticket` where creation>=%(since)s
        {emp_filter} group by status""", params, as_dict=True)
    by_cat = frappe.db.sql(f"""select category, count(*) n, sum(sla_status='Breached') breached,
        avg(timestampdiff(MINUTE, creation, first_responded_on))/60 frt,
        avg(timestampdiff(MINUTE, creation, resolved_on))/60 rt, avg(nullif(rating,0))*5 csat
        from `tabESS HR Ticket` where creation>=%(since)s {emp_filter} group by category""", params, as_dict=True)
    total = sum(r.n for r in by_cat) or 0
    breached = sum(cint(r.breached) for r in by_cat)
    docs = frappe.db.sql(f"""select status, count(*) n from `tabESS Document Request` where creation>=%(since)s
        {emp_filter} group by status""", params, as_dict=True)
    expiring = frappe.db.sql(f"""select document_type, count(*) n from `tabESS Employee Document`
        where expiry_date between %(today)s and %(horizon)s {emp_filter} group by document_type""",
                             {**params, "today": today(), "horizon": add_days(today(), 60)}, as_dict=True)
    att = frappe.db.sql(f"""select count(*) n from `tabAttendance Request` where docstatus=0
        and creation>=%(since)s {emp_filter}""", params)[0][0]
    adoption = frappe.db.sql("""select date(creation) d, count(distinct user) n from `tabESS Audit Event`
        where event_type='Session' and creation>=%s group by d order by d""", add_days(today(), -30), as_dict=True)
    headcount = frappe.db.sql(f"""select department, count(*) n from `tabEmployee` where status='Active'
        {emp_filter.replace('employee in', 'name in')} group by department""", params, as_dict=True)
    return {
        "tickets_by_status": tickets, "by_category": by_cat,
        "sla_compliance": round(100 * (total - breached) / total, 1) if total else None,
        "documents_by_status": docs, "expiring_documents": expiring, "open_attendance_corrections": att,
        "adoption": adoption, "headcount": suppress([dict(r) for r in headcount]),
    }


def build_snapshots():
    d = today()
    for company in frappe.get_all("Company", pluck="name"):
        emps = frappe.get_all("Employee", filters={"company": company, "status": "Active"}, pluck="name")
        if not emps:
            continue
        metrics = {
            "headcount": len(emps),
            "on_leave": frappe.db.count("Leave Application", {"employee": ["in", emps], "docstatus": 1,
                                                                "status": "Approved", "from_date": ["<=", d],
                                                                "to_date": [">=", d]}),
            "open_tickets": frappe.db.count("ESS HR Ticket", {"employee": ["in", emps],
                                                               "status": ["not in", ["Resolved", "Closed"]]}),
            "missing_punches": frappe.db.count("Attendance", {"employee": ["in", emps], "docstatus": 1,
                                                               "attendance_date": add_days(d, -1),
                                                               "status": "Absent"}),
        }
        for metric, value in metrics.items():
            frappe.get_doc({"doctype": "ESS Analytics Snapshot", "snapshot_date": d, "company": company,
                            "metric": metric, "value": value, "population": len(emps)}).insert(ignore_permissions=True)
