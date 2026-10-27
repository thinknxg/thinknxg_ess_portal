import frappe
from frappe.utils import today, add_days, getdate, nowdate, get_first_day
from thinknxg_ess_portal.api._guard import guard
from thinknxg_ess_portal.services import identity, hrms


@frappe.whitelist(methods=["GET"])
def get_summary():
    emp = guard()
    d = today()
    s = identity.settings()
    out = {"employee": emp.employee_name, "date": d}

    if s.enable_attendance:
        from thinknxg_ess_portal.api.attendance import _today_state
        out["attendance"] = _today_state(emp)
    if s.enable_leave:
        from thinknxg_ess_portal.api.leave import _balances
        try:
            out["leave_balances"] = _balances(emp.name)[:4]
        except Exception:
            out["leave_balances"] = []
    if s.enable_payroll:
        slip = frappe.get_all("Salary Slip", filters={"employee": emp.name, "docstatus": 1}, limit=1,
                              order_by="end_date desc", fields=["name", "start_date", "end_date", "net_pay", "currency"])
        out["latest_payslip"] = slip[0] if slip else None
    out["holidays"] = [h for h in hrms.holidays_between(emp.name, d, add_days(d, 120)) if not h.weekly_off][:3]
    out["pending_requests"] = {
        "leave": frappe.db.count("Leave Application", {"employee": emp.name, "docstatus": 0, "status": "Open"}),
        "expense": frappe.db.count("Expense Claim", {"employee": emp.name, "docstatus": 0}),
        "tickets": frappe.db.count("ESS HR Ticket", {"employee": emp.name, "status": ["not in", ["Resolved", "Closed"]]}),
        "documents": frappe.db.count("ESS Document Request", {"employee": emp.name,
                                                               "status": ["in", ["Requested", "Pending Approval", "Approved"]]}),
    }
    out["expiring_documents"] = frappe.get_all("ESS Employee Document", fields=["name", "document_type", "expiry_date"],
                                               filters={"employee": emp.name,
                                                        "expiry_date": ["between", [d, add_days(d, s.document_expiry_alert_days or 30)]]})
    from thinknxg_ess_portal.api.announcements import _visible_announcements
    out["announcements"] = _visible_announcements(emp, limit=3)
    out["celebrations"] = _celebrations(emp)
    out["activity"] = frappe.get_all("Notification Log", filters={"for_user": frappe.session.user},
                                     fields=["name", "subject", "document_type", "document_name", "creation", "read"],
                                     order_by="creation desc", limit=8)
    from thinknxg_ess_portal.api.inbox import _collect
    out["inbox_count"] = len(_collect(emp))
    if s.enable_recognition:
        out["recognition"] = frappe.get_all("ESS Recognition", filters={"status": "Approved", "visibility": "Public"},
                                            fields=["name", "sender_name", "recipient_name", "category", "message",
                                                    "posted_on"], order_by="posted_on desc", limit=3)
    if identity.is_manager():
        from thinknxg_ess_portal.services.workflow import pending
        out["team"] = {"pending_approvals": len(pending()), "size": len(identity.team_employees())}
    return out


def _celebrations(emp):
    """Birthdays (day/month only) and work anniversaries this week within the employee's company."""
    d = getdate(today())
    days = [add_days(d, i) for i in range(7)]
    md = [(x.month, x.day) for x in days]
    rows = frappe.get_all("Employee", filters={"company": emp.company, "status": "Active"},
                          fields=["name", "employee_name", "image", "date_of_birth", "date_of_joining", "department"],
                          limit=5000)
    out = []
    for r in rows:
        if r.date_of_birth and (r.date_of_birth.month, r.date_of_birth.day) in md:
            out.append({"type": "birthday", "employee_name": r.employee_name, "image": r.image,
                        "day": f"{r.date_of_birth.day:02d}-{r.date_of_birth.month:02d}"})
        if r.date_of_joining and (r.date_of_joining.month, r.date_of_joining.day) in md and r.date_of_joining.year < d.year:
            out.append({"type": "anniversary", "employee_name": r.employee_name, "image": r.image,
                        "years": d.year - r.date_of_joining.year,
                        "day": f"{r.date_of_joining.day:02d}-{r.date_of_joining.month:02d}"})
    return out[:8]
