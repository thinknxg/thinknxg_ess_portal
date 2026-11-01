"""Geofence evaluation. Pure functions: no frappe imports, so they are unit-tested in CI without a site."""
import math

EARTH_RADIUS_M = 6371008.8

# Decision codes shared with the API and the UI.
OK_MATCHED = "MATCHED"
OK_RECORDED = "RECORDED"
OK_NOT_REQUIRED = "LOCATION_NOT_REQUIRED"
LOCATION_REQUIRED = "LOCATION_REQUIRED"
INVALID_LOCATION = "INVALID_LOCATION"
LOCATION_INACCURATE = "LOCATION_INACCURATE"
NO_LOCATIONS = "NO_LOCATIONS_CONFIGURED"
OUTSIDE_GEOFENCE = "OUTSIDE_GEOFENCE"


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def valid_coords(lat, lng):
    return lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180 and not (lat == 0 and lng == 0)


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def nearest(lat, lng, candidates):
    best, best_d = None, None
    for c in candidates:
        d = haversine_m(lat, lng, float(c["latitude"]), float(c["longitude"]))
        if best_d is None or d < best_d:
            best, best_d = c, d
    return best, best_d


def evaluate_location(lat, lng, accuracy, *, required, enforce, max_accuracy, candidates):
    """Decide whether a reported fix satisfies the geofence policy.

    The fix's centre must lie inside a permitted location's radius, and the device-reported accuracy must be
    no worse than ``max_accuracy``. We do not stretch the radius by the accuracy: a poor fix is rejected
    with a specific message instead, which is easier for employees to act on.
    """
    lat, lng, accuracy = _num(lat), _num(lng), _num(accuracy)
    out = {"ok": True, "code": OK_NOT_REQUIRED, "matched": None, "distance": None, "nearest": None,
           "nearest_distance": None, "accuracy": accuracy, "max_accuracy": max_accuracy}
    have = lat is not None and lng is not None
    if have and not valid_coords(lat, lng):
        if required:
            return {**out, "ok": False, "code": INVALID_LOCATION}
        have = False
    if have and candidates:
        n, d = nearest(lat, lng, candidates)
        out.update(nearest=n, nearest_distance=round(d, 1))
    if not required:
        return out
    if not have:
        return {**out, "ok": False, "code": LOCATION_REQUIRED}
    if accuracy is None or accuracy < 0 or (max_accuracy and accuracy > max_accuracy):
        return {**out, "ok": False, "code": LOCATION_INACCURATE}
    if not enforce:
        return {**out, "code": OK_RECORDED}
    if not candidates:
        return {**out, "ok": False, "code": NO_LOCATIONS}
    inside = []
    for c in candidates:
        d = haversine_m(lat, lng, float(c["latitude"]), float(c["longitude"]))
        if d <= float(c["radius"]):
            inside.append((d, c))
    if inside:
        inside.sort(key=lambda x: x[0])
        d, c = inside[0]
        return {**out, "code": OK_MATCHED, "matched": c, "distance": round(d, 1)}
    return {**out, "ok": False, "code": OUTSIDE_GEOFENCE}


def risk_flags(lat, lng, accuracy, now, previous=None, max_speed_kmh=300, seen_elsewhere=()):
    """Heuristic signals of spoofed or replayed locations. They are flags for review, not proof.

    previous: (lat, lng, datetime) of the employee's last located punch.
    seen_elsewhere: set of (round(lat, 6), round(lng, 6)) reported on *other* days.
    """
    lat, lng, accuracy = _num(lat), _num(lng), _num(accuracy)
    flags = []
    if lat is None or lng is None:
        return flags
    if accuracy is not None and accuracy < 1:
        flags.append("unrealistic_accuracy")
    if previous and previous[0] is not None and previous[2] is not None:
        secs = (now - previous[2]).total_seconds()
        dist = haversine_m(lat, lng, float(previous[0]), float(previous[1]))
        if secs > 0 and dist > 1000 and (dist / secs) * 3.6 > max_speed_kmh:
            flags.append("impossible_travel")
    if (round(lat, 6), round(lng, 6)) in set(seen_elsewhere):
        flags.append("identical_coordinates")
    return flags


def risk_level(flags):
    if not flags:
        return "None"
    if "impossible_travel" in flags or len(flags) >= 2:
        return "High"
    return "Low"
