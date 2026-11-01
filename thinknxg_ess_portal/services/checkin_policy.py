"""ESS check-in policy engine.

resolve()  -> the effective policy for an employee (global settings + employee override), with a readable trace.
evaluate() -> a decision for one punch: sequence, shift window, GPS/geofence, risk. Never inserts anything.

Scope: only ESS Portal punches. Biometric devices, the Employee Checkin API and Desk are separate channels and
are deliberately untouched, so turning ESS check-in off never stops a device integration.
"""
import json
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, formatdate, get_datetime, getdate, now_datetime
from thinknxg_ess_portal.services import geo, identity, shifts

ENFORCE_GLOBAL = "Enforce global setting for everyone"
RECORD_ONLY = "Record location only"


def _hm(dt):
    return get_datetime(dt).strftime("%H:%M")


def _when(dt, now):
    dt = get_datetime(dt)
    if dt.date() == now.date():
        return _hm(dt)
    if dt.date() == (now + timedelta(days=1)).date():
        return _("tomorrow at {0}").format(_hm(dt))
    return _("{0} at {1}").format(formatdate(dt.date(), "EEE d MMM"), _hm(dt))


def _distance(m):
    return f"{m / 1000:.1f} km" if m >= 1000 else f"{int(round(m))} m"


def _locations_cache():
    data = frappe.cache.get_value("ess_checkin_locations")
    if data is None:
        data = [dict(r) for r in frappe.get_all(
            "ESS Checkin Location", filters={"is_active": 1},
            fields=["name", "latitude", "longitude", "radius", "applies_to", "company", "branch", "department"])]
        frappe.cache.set_value("ess_checkin_locations", data, expires_in_sec=600)
    return data


def clear_location_cache(doc=None, method=None):
    frappe.cache.delete_value("ess_checkin_locations")


def override_for(employee, on_date=None):
    on_date = getdate(on_date)
    row = frappe.db.get_value("ESS Checkin Policy", {"employee": employee, "is_active": 1},
                              ["name", "checkin_access", "gps_requirement", "shift_window", "radius_override",
                               "accuracy_override", "location_mode", "valid_from", "valid_until", "reason"], as_dict=True)
    if not row:
        return None
    if (row.valid_from and getdate(row.valid_from) > on_date) or (row.valid_until and getdate(row.valid_until) < on_date):
        return None
    row.locations = frappe.get_all("ESS Checkin Policy Location", filters={"parent": row.name,
                                                                           "parenttype": "ESS Checkin Policy"},
                                   pluck="location", order_by="idx asc")
    return row


def resolve(employee, at=None, settings=None):
    s = settings or identity.settings()
    at = at or now_datetime()
    overrides_on = s.get("checkin_policy_mode") != ENFORCE_GLOBAL
    trace = []
    enabled = bool(cint(s.get("enable_checkin")))
    trace.append(_("Global employee check-in is {0}.").format(_("on") if enabled else _("off")))
    gps = bool(cint(s.get("require_geolocation")))
    window = bool(cint(s.get("enforce_shift_window")))
    radius = cint(s.get("default_geofence_radius")) or 150
    accuracy = cint(s.get("max_gps_accuracy")) or 50
    radius_overridden = False
    ov = override_for(employee, getdate(at)) if (overrides_on and employee) else None
    if not overrides_on:
        trace.append(_("The global setting is enforced for everyone, so employee overrides are ignored."))
    if ov:
        trace.append(_("Employee override {0} applies: {1}").format(ov.name, ov.reason or "-"))
        if ov.checkin_access == "Allow":
            enabled = True
            trace.append(_("Override allows portal check-in."))
        elif ov.checkin_access == "Deny":
            enabled = False
            trace.append(_("Override blocks portal check-in."))
        if ov.gps_requirement == "Required":
            gps = True
            trace.append(_("Override requires GPS."))
        elif ov.gps_requirement == "Exempt":
            gps = False
            trace.append(_("Override exempts this employee from GPS."))
        if ov.shift_window == "Enforce":
            window = True
        elif ov.shift_window == "Don't enforce":
            window = False
        if ov.radius_override:
            radius, radius_overridden = cint(ov.radius_override), True
        if ov.accuracy_override:
            accuracy = cint(ov.accuracy_override)
    return frappe._dict(
        enabled=enabled, gps_required=gps, enforce_geofence=s.get("geofence_enforcement") != RECORD_ONLY,
        radius=radius, radius_overridden=radius_overridden, max_accuracy=accuracy, shift_window=window,
        allow_without_shift=bool(cint(s.get("allow_checkin_without_shift"))), cooldown=cint(s.get("checkin_cooldown_minutes")),
        overrides_on=overrides_on, override=ov.name if ov else None,
        location_mode=ov.location_mode if ov else None, override_locations=ov.locations if ov else [],
        trace=trace)


def summary(p):
    parts = [_("Portal check-in enabled.") if p.enabled else _("Portal check-in disabled.")]
    if p.get("overrides_on") is not None:
        parts.append(_("Employee-specific allow/deny rules can override the default.") if p.overrides_on
                     else _("The global setting applies to everyone."))
    if p.gps_required:
        geo_part = (_("GPS required; {0} m radius and {1} m accuracy limit.") if p.enforce_geofence
                    else _("GPS location recorded (not enforced); {1} m accuracy limit.")).format(p.radius, p.max_accuracy)
        parts.append(geo_part)
    else:
        parts.append(_("GPS not required."))
    parts.append(_("Check-in only during the assigned shift window.") if p.shift_window
                 else _("Check-in permitted outside shifts unless another policy restricts it."))
    return " ".join(parts)


def _applies(loc, emp):
    a = loc.get("applies_to") or "All Employees"
    if a == "All Employees":
        return True
    if a == "Company":
        return loc.get("company") == emp.get("company")
    if a == "Branch":
        return bool(loc.get("branch")) and loc.get("branch") == emp.get("branch")
    if a == "Department":
        return bool(loc.get("department")) and loc.get("department") == emp.get("department")
    return False


def candidate_locations(emp, p, shift_location=None, settings=None):
    s = settings or identity.settings()
    out, seen = [], set()
    only = p.location_mode == "Only these locations"
    every = _locations_cache()

    def add(name, lat, lng, radius, source):
        if not lat or not lng or name in seen:
            return
        seen.add(name)
        out.append({"name": name, "latitude": float(lat), "longitude": float(lng),
                    "radius": int(p.radius if p.radius_overridden else (radius or p.radius)), "source": source})

    if not only:
        if cint(s.get("use_shift_location")) and shift_location and frappe.db.exists("DocType", "Shift Location"):
            sl = frappe.db.get_value("Shift Location", shift_location,
                                     ["location_name", "latitude", "longitude", "checkin_radius"], as_dict=True)
            if sl:
                add(sl.location_name or shift_location, sl.latitude, sl.longitude, sl.checkin_radius, "Shift Location")
        if cint(s.get("use_ess_locations")):
            for loc in every:
                if _applies(loc, emp):
                    add(loc["name"], loc["latitude"], loc["longitude"], loc["radius"], "ESS location")
    listed = set(p.override_locations or [])
    for loc in every:
        if loc["name"] in listed:
            add(loc["name"], loc["latitude"], loc["longitude"], loc["radius"], "Employee policy")
    return out


def session_state(employee, now):
    """Last typed punch in the past 20 hours. Untyped device logs are ignored for sequencing."""
    logs = frappe.get_all("Employee Checkin", filters={"employee": employee, "time": [">=", add_to_date(now, hours=-20)],
                                                       "log_type": ["in", ["IN", "OUT"]]},
                          fields=["name", "time", "log_type", "device_id"], order_by="time asc")
    last = logs[-1] if logs else None
    open_in = last if last and last.log_type == "IN" else None
    return frappe._dict(logs=logs, last=last, open_in=open_in, next_action="OUT" if open_in else "IN")


def _risk(emp_name, lat, lng, accuracy, now, s):
    meta = frappe.get_meta("Employee Checkin")
    if not meta.has_field("latitude"):
        return []
    prev = frappe.get_all("Employee Checkin", filters={"employee": emp_name, "latitude": ["is", "set"],
                                                       "time": ["<", now]},
                          fields=["latitude", "longitude", "time"], order_by="time desc", limit=1)
    previous = (prev[0].latitude, prev[0].longitude, get_datetime(prev[0].time)) if prev else None
    seen = {(round(float(r.latitude), 6), round(float(r.longitude), 6)) for r in frappe.get_all(
        "Employee Checkin", filters={"employee": emp_name, "latitude": ["is", "set"],
                                     "time": ["between", [add_to_date(now, days=-30), f"{now.date()} 00:00:00"]]},
        fields=["latitude", "longitude"], limit=200) if r.latitude and r.longitude}
    return geo.risk_flags(lat, lng, accuracy, now, previous=previous,
                          max_speed_kmh=cint(s.get("max_travel_speed_kmh")) or 300, seen_elsewhere=seen)


LOCATION_MESSAGES = {
    geo.LOCATION_REQUIRED: (_("Location is required to check in."),
                            _("Allow location access for this site in your browser, then try again.")),
    geo.INVALID_LOCATION: (_("Your device returned an invalid location."),
                           _("Turn location off and on again, wait a few seconds, then try again.")),
    geo.NO_LOCATIONS: (_("No check-in location is set up for you yet."),
                       _("Ask HR to add your work location before checking in from the portal.")),
}


def evaluate(emp, log_type, latitude=None, longitude=None, accuracy=None, now=None):
    """Decide one punch. `emp` is the session employee row (name, company, branch, department)."""
    s = identity.settings()
    now = now or now_datetime()
    p = resolve(emp.name, now, s)
    res = frappe._dict(allowed=False, code=None, message=None, hint=None, log_type=log_type, policy=p, window=None,
                       next_window=None, location=None, candidates=[], risk_flags=[], risk_level="None",
                       warnings=[], trace=list(p.trace), now=now)

    def deny(code, message, hint=None):
        res.update(code=code, message=message, hint=hint)
        res.trace.append(f"DENIED {code}: {message}")
        return res

    if log_type not in ("IN", "OUT"):
        return deny("INVALID_ACTION", _("Unknown punch type."))
    if not p.enabled:
        return deny("CHECKIN_DISABLED", _("Portal check-in is turned off for your account."),
                    _("Use the attendance device at your site, or contact HR if you think this is wrong."))

    st = session_state(emp.name, now)
    res.session = st
    if log_type == "IN" and st.open_in:
        return deny("ALREADY_CHECKED_IN", _("You're already checked in since {0}.").format(_when(st.open_in.time, now)),
                    _("Check out first."))
    if log_type == "OUT" and not st.open_in:
        return deny("NOT_CHECKED_IN", _("You haven't checked in yet."), _("Check in first."))
    if p.cooldown and st.last and get_datetime(st.last.time) > add_to_date(now, minutes=-p.cooldown):
        return deny("COOLDOWN", _("Please wait {0} minute(s) between punches.").format(p.cooldown))

    cur = shifts.current_window(emp.name, now)
    res.window = cur
    today = shifts.plan([emp.name], now.date(), now.date())[emp.name][0]
    if log_type == "IN":
        if cur:
            res.trace.append(_("Within the {0} window ({1}–{2}).").format(cur["shift_type"], _hm(cur["open"]), _hm(cur["close"])))
        elif p.shift_window:
            nxt = shifts.next_window(emp.name, now)
            res.next_window = nxt
            closed = [x for x in today["windows"] if x["close"] < now]
            if nxt and (nxt["open"] - now).total_seconds() < 36 * 3600:
                return deny("OUTSIDE_SHIFT_WINDOW",
                            _("Check-in opens {0}, {1} minutes before your {2} shift.").format(
                                _when(nxt["open"], now), int((nxt["start"] - nxt["open"]).total_seconds() // 60),
                                nxt["shift_type"]),
                            _("Your shift starts {0}.").format(_when(nxt["start"], now)))
            if closed:
                return deny("OUTSIDE_SHIFT_WINDOW", _("Your check-in window for {0} closed at {1}.").format(
                    closed[-1]["shift_type"], _hm(closed[-1]["close"])),
                    _("If you worked this shift, request an attendance correction."))
            return deny("NO_SHIFT", _("You have no shift scheduled now, and check-in is only allowed during shift windows."),
                        _("If you're working, ask your manager to add you to the roster."))
        elif not today["windows"] and not p.allow_without_shift:
            reason = (_("today is a rest day on your roster") if today["rest_day"] else
                      _("today is a holiday ({0})").format(today["holiday"]["description"]) if today["holiday"] else
                      _("you have no shift today"))
            return deny("NO_SHIFT", _("Check-in isn't available because {0}.").format(reason),
                        _("If you're working, ask your manager to add you to the roster, or request an attendance correction."))
    elif p.shift_window and not cur:
        res.warnings.append(_("This check-out is after your shift window closed, so Frappe HR may not link it to the shift."))

    if today["leave"] and today["leave"]["status"] == "Approved" and not today["leave"]["half_day"]:
        res.warnings.append(_("You're on approved {0} today.").format(today["leave"]["leave_type"]))

    ref = cur or (today["windows"][0] if today["windows"] else None)
    shift_location = ref["location"] if ref else None
    cands = candidate_locations(emp, p, shift_location, s)
    res.candidates = [{"name": c["name"], "radius": c["radius"], "source": c["source"]} for c in cands]
    loc = geo.evaluate_location(latitude, longitude, accuracy, required=p.gps_required, enforce=p.enforce_geofence,
                                max_accuracy=p.max_accuracy, candidates=cands)
    res.location = loc
    if not loc["ok"]:
        code = loc["code"]
        if code == geo.LOCATION_INACCURATE:
            if loc["accuracy"] is None:
                msg = _("Your device didn't report how accurate its location is.")
            else:
                msg = _("Your location is accurate to ±{0} m, but check-in needs ±{1} m or better.").format(
                    int(round(loc["accuracy"])), p.max_accuracy)
            return deny(code, msg, _("Turn on precise location, move near a window or outdoors, wait a few seconds, then try again."))
        if code == geo.OUTSIDE_GEOFENCE:
            n = loc["nearest"]
            return deny(code, _("You're {0} from {1}. Check-in is allowed within {2} m.").format(
                _distance(loc["nearest_distance"]), n["name"], n["radius"]),
                _("Move closer to your work location and try again. Working elsewhere today? Ask your manager or request an attendance correction."))
        msg, hint = LOCATION_MESSAGES.get(code, (_("Location check failed."), None))
        return deny(code, msg, hint)
    if loc["matched"]:
        res.trace.append(_("Inside {0} ({1} from the centre, radius {2} m).").format(
            loc["matched"]["name"], _distance(loc["distance"]), loc["matched"]["radius"]))

    if cint(s.get("flag_location_risk")) and latitude not in (None, ""):
        res.risk_flags = _risk(emp.name, latitude, longitude, accuracy, now, s)
        res.risk_level = geo.risk_level(res.risk_flags)
        if res.risk_flags:
            res.trace.append(_("Risk flags: {0}").format(", ".join(res.risk_flags)))
        if res.risk_level == "High" and cint(s.get("block_high_risk_checkins")):
            return deny("HIGH_RISK", _("We couldn't verify this location."),
                        _("Contact HR. Location tools that change your reported position can block check-in."))

    res.update(allowed=True, code="ALLOWED")
    res.trace.append("ALLOWED")
    return res


def public_result(res):
    """Response shape for the portal. Never includes other locations' coordinates."""
    loc = res.location or {}
    matched = loc.get("matched") or {}
    nearest = loc.get("nearest") or {}
    wn = res.window or res.next_window
    return {
        "ok": bool(res.allowed), "code": res.code, "message": res.message, "hint": res.hint, "log_type": res.log_type,
        "warnings": res.warnings, "location": {
            "code": loc.get("code"), "matched": matched.get("name"), "distance": loc.get("distance"),
            "nearest": nearest.get("name"), "nearest_distance": loc.get("nearest_distance"),
            "nearest_radius": nearest.get("radius"), "accuracy": loc.get("accuracy"), "max_accuracy": res.policy.max_accuracy},
        "window": shifts.format_window(wn) if wn else None, "risk_level": res.risk_level,
    }


def write_log(emp, res, latitude=None, longitude=None, accuracy=None, client_time=None, checkin=None, source=None):
    loc = res.location or {}
    wn = res.window or res.next_window
    ua = ""
    try:
        ua = (frappe.get_request_header("User-Agent") or "")[:500]
    except Exception:
        pass
    ct = None
    if client_time:
        try:
            ct = get_datetime(str(client_time).replace("T", " ")[:19])
        except Exception:
            ct = None
    doc = frappe.get_doc({
        "doctype": "ESS Checkin Log", "employee": emp.name, "employee_name": emp.employee_name,
        "user": frappe.session.user, "log_type": res.log_type if res.log_type in ("IN", "OUT") else None,
        "decision": "Allowed" if res.allowed else "Denied", "reason_code": res.code,
        "message": res.message or "; ".join(res.warnings), "server_time": res.now, "client_time": ct,
        "source": source or "ESS Portal", "checkin": checkin, "policy_override": res.policy.override,
        "latitude": geo._num(latitude), "longitude": geo._num(longitude), "accuracy": geo._num(accuracy),
        "matched_location": (loc.get("matched") or {}).get("name"), "distance_m": loc.get("distance"),
        "nearest_location": (loc.get("nearest") or {}).get("name"), "nearest_distance_m": loc.get("nearest_distance"),
        "shift_type": wn["shift_type"] if wn else None, "window_open": wn["open"] if wn else None,
        "window_close": wn["close"] if wn else None, "risk_level": res.risk_level,
        "risk_flags": ", ".join(res.risk_flags), "ip_address": getattr(frappe.local, "request_ip", None),
        "user_agent": ua,
        "policy_trace": json.dumps({"trace": res.trace, "warnings": res.warnings, "candidates": res.candidates,
                                    "policy": {k: v for k, v in res.policy.items() if k != "trace"}}, default=str, indent=1),
    })
    doc.insert(ignore_permissions=True)
    return doc.name
