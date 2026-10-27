import math
import frappe
from frappe import _
from frappe.utils import (now_datetime, today, getdate, get_first_day, get_last_day, add_to_date, cint, flt,
                          get_datetime, date_diff, add_days)
from thinknxg_ess_portal.api._guard import guard, page
from thinknxg_ess_portal.services import identity, hrms
from thinknxg_ess_portal.services.idempotency import run_once


def _checkins(employee, date):
    return frappe.get_all("Employee Checkin", filters={"employee": employee, "time": ["between", [
        f"{date} 00:00:00", f"{date} 23:59:59"]]}, fields=["name", "time", "log_type", "device_id"],
                          order_by="time asc")


def _today_state(emp):
    d = today()
    logs = _checkins(emp.name, d)
    shift = hrms.active_shift(emp.name, d)
    att = frappe.db.get_value("Attendance", {"employee": emp.name, "attendance_date": d, "docstatus": 1},
                              ["status", "in_time", "out_time", "late_entry", "early_exit"], as_dict=True)
    on_leave = frappe.db.exists("Leave Application", {"employee": emp.name, "docstatus": 1, "status": "Approved",
                                                      "from_date": ["<=", d], "to_date": [">=", d]})
    last = logs[-1].log_type if logs else None
    s = identity.settings()
    return {
        "date": d, "shift": {k: v for k, v in (shift or {}).items() if k != "location"} if shift else None,
        "geofence": {"name": shift["location"].location_name, "radius": shift["location"].checkin_radius}
        if shift and shift.get("location") else None,
        "logs": [{"time": str(l.time), "log_type": l.log_type} for l in logs],
        "next_action": "OUT" if last == "IN" else "IN",
        "attendance": att, "on_leave": bool(on_leave),
        "checkin_enabled": bool(s.enable_checkin), "require_geolocation": bool(s.require_geolocation),
        "first_in": str(logs[0].time) if logs and logs[0].log_type == "IN" else None,
    }


def _haversine(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _punch(log_type, latitude=None, longitude=None, accuracy=None, client_request_id=None):
    emp = guard("enable_checkin")
    s = identity.settings()

    def do():
        now = now_datetime()
        shift = hrms.active_shift(emp.name, now.date())
        if not shift and not s.allow_checkin_without_shift:
            frappe.throw(_("You don't have an active shift today. Please contact your manager."))
        logs = _checkins(emp.name, now.date())
        if logs and logs[-1].log_type == log_type:
            frappe.throw(_("You are already checked {0}.").format(_("in") if log_type == "IN" else _("out")))
        if log_type == "OUT" and not logs:
            frappe.throw(_("Please check in first."))
        cooldown = cint(s.checkin_cooldown_minutes)
        if logs and cooldown and get_datetime(logs[-1].time) > add_to_date(now, minutes=-cooldown):
            frappe.throw(_("Please wait {0} minute(s) between punches.").format(cooldown))
        lat, lng = (flt(latitude) if latitude not in (None, "") else None,
                    flt(longitude) if longitude not in (None, "") else None)
        if s.require_geolocation and (lat is None or lng is None):
            frappe.throw(_("Location is required to check {0}. Please allow location access.").format(
                _("in") if log_type == "IN" else _("out")))
        loc = shift.get("location") if shift else None
        if loc and loc.latitude and loc.longitude and loc.checkin_radius:
            if lat is None:
                frappe.throw(_("Location is required for your shift location."))
            dist = _haversine(lat, lng, flt(loc.latitude), flt(loc.longitude))
            if dist > flt(loc.checkin_radius) + min(flt(accuracy or 0), 100):
                frappe.throw(_("You are {0} m away from {1}. Check-in is allowed within {2} m.").format(
                    int(dist), loc.location_name, int(loc.checkin_radius)))
        meta = frappe.get_meta("Employee Checkin")
        doc = {"doctype": "Employee Checkin", "employee": emp.name, "time": now, "log_type": log_type,
               "device_id": "thinkNXG ESS Portal"}
        if lat is not None and meta.has_field("latitude"):
            doc.update({"latitude": lat, "longitude": lng})
        ci = frappe.get_doc(doc)
        ci.flags.ignore_permissions = True
        ci.insert()
        return {"doctype": "Employee Checkin", "name": ci.name, "time": str(ci.time), "log_type": log_type}

    return run_once(client_request_id, f"checkin_{log_type.lower()}", do)


@frappe.whitelist(methods=["GET"])
def get_today():
    emp = guard("enable_attendance")
    return _today_state(emp)


@frappe.whitelist(methods=["POST"])
def check_in(latitude=None, longitude=None, accuracy=None, client_request_id=None):
    return _punch("IN", latitude, longitude, accuracy, client_request_id)


@frappe.whitelist(methods=["POST"])
def check_out(latitude=None, longitude=None, accuracy=None, client_request_id=None):
    return _punch("OUT", latitude, longitude, accuracy, client_request_id)


@frappe.whitelist(methods=["GET"])
def get_month(year=None, month=None):
    emp = guard("enable_attendance")
    start = getdate(f"{cint(year) or getdate().year}-{cint(month) or getdate().month:02d}-01")
    end = get_last_day(start)
    att = {str(a.attendance_date): a for a in frappe.get_all(
        "Attendance", filters={"employee": emp.name, "docstatus": 1, "attendance_date": ["between", [start, end]]},
        fields=["name", "attendance_date", "status", "in_time", "out_time", "late_entry", "early_exit", "leave_type",
                "shift", "working_hours"])}
    logs = {}
    for l in frappe.get_all("Employee Checkin", filters={"employee": emp.name,
                                                         "time": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]},
                            fields=["time", "log_type"], order_by="time asc"):
        logs.setdefault(str(getdate(l.time)), []).append({"time": str(l.time)[11:16], "log_type": l.log_type})
    hol = {str(h.holiday_date): h for h in hrms.holidays_between(emp.name, start, end)}
    days = []
    for i in range(date_diff(end, start) + 1):
        d = str(add_days(start, i))
        a = att.get(d)
        status = a.status if a else ("Holiday" if d in hol and not hol[d].weekly_off else
                                     "Weekly Off" if d in hol else ("Future" if d > today() else
                                                                    ("Missing" if logs.get(d) else "Unmarked")))
        days.append({"date": d, "status": status, "late": bool(a and a.late_entry),
                     "early_exit": bool(a and a.early_exit), "working_hours": a.working_hours if a else None,
                     "leave_type": a.leave_type if a else None, "logs": logs.get(d, []),
                     "holiday": hol[d].description if d in hol else None,
                     "incomplete": bool(logs.get(d)) and len(logs.get(d)) % 2 == 1 and d < today()})
    summary = {}
    for d in days:
        summary[d["status"]] = summary.get(d["status"], 0) + 1
    summary["late"] = sum(1 for d in days if d["late"])
    return {"start": str(start), "end": str(end), "days": days, "summary": summary}


@frappe.whitelist(methods=["POST"])
def request_correction(from_date, to_date, reason="On Duty", explanation=None, half_day=0, half_day_date=None,
                       client_request_id=None):
    emp = guard("enable_attendance")
    if reason not in ("Work From Home", "On Duty"):
        frappe.throw(_("Invalid reason"))
    if getdate(from_date) > getdate(to_date):
        frappe.throw(_("From date must be before to date"))
    if getdate(to_date) > getdate(add_days(today(), 31)):
        frappe.throw(_("Corrections can only be requested up to 31 days ahead."))
    if not (explanation or "").strip():
        frappe.throw(_("Please explain the correction."))

    def do():
        doc = frappe.get_doc({"doctype": "Attendance Request", "employee": emp.name, "company": emp.company,
                              "from_date": from_date, "to_date": to_date, "reason": reason,
                              "explanation": explanation[:1000], "half_day": cint(half_day),
                              "half_day_date": half_day_date if cint(half_day) else None})
        doc.insert(ignore_permissions=True)
        approvers = [u for u in frappe.get_all("Employee", filters={"name": emp.reports_to}, pluck="user_id") if u] \
            if emp.reports_to else []
        from thinknxg_ess_portal.services.notifications import notify
        for u in approvers:
            notify(u, "Approvals", _("Attendance correction from {0}").format(emp.employee_name),
                   f"{from_date} → {to_date}", "/ess/team/approvals", doc.doctype, doc.name)
        return {"doctype": doc.doctype, "name": doc.name}

    return run_once(client_request_id, "attendance_correction", do)


@frappe.whitelist(methods=["GET"])
def my_corrections(limit=20, offset=0):
    emp = guard("enable_attendance")
    limit, offset = page(limit, offset)
    fields = ["name", "from_date", "to_date", "reason", "explanation", "docstatus", "creation"]
    if frappe.get_meta("Attendance Request").has_field("ess_status"):
        fields += ["ess_status", "ess_review_comment"]
    rows = frappe.get_all("Attendance Request", filters={"employee": emp.name}, fields=fields,
                          order_by="creation desc", limit=limit, start=offset)
    for r in rows:
        r["status"] = ("Approved" if r.docstatus == 1 else "Cancelled" if r.docstatus == 2 else
                       "Rejected" if r.get("ess_status") == "Rejected" else "Pending")
    return rows
