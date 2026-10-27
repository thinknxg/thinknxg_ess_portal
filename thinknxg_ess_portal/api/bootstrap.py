import frappe
from frappe.utils import today
from thinknxg_ess_portal.services import identity
from thinknxg_ess_portal.services.audit import log_event

PUBLIC_SETTINGS = ["portal_title", "brand_color", "logo", "default_language", "weekend_days", "support_email",
                   "vapid_public_key", "pwa_theme_color", "ai_system_notice", "monthly_points_budget",
                   "allow_public_recognition", "show_team_availability", "require_geolocation"]


@frappe.whitelist(methods=["GET"])
def get_boot():
    identity.require_login()
    user = frappe.session.user
    s = identity.settings()
    emp = identity.get_employee(required=False)
    key = f"ess_session:{user}:{today()}"
    if not frappe.cache.get_value(key):
        frappe.cache.set_value(key, 1, expires_in_sec=86400)
        log_event("Session", details="portal opened", employee=emp.name if emp else None)
    lang = frappe.db.get_value("User", user, "language") or s.default_language or "en"
    return {
        "user": {"name": user, "full_name": frappe.utils.get_fullname(user),
                 "image": frappe.db.get_value("User", user, "user_image"), "email": user},
        "employee": {k: (str(v) if v is not None else None) for k, v in (emp or {}).items()
                     if k in ("name", "employee_name", "first_name", "designation", "department", "company",
                              "branch", "image", "date_of_joining")} if emp else None,
        "capabilities": identity.capabilities(),
        "settings": {k: s.get(k) for k in PUBLIC_SETTINGS},
        "lang": "ar" if str(lang).startswith("ar") else "en",
        "server_date": today(),
        "unread": frappe.db.count("Notification Log", {"for_user": user, "read": 0}),
    }
