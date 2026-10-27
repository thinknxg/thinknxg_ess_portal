import frappe
from urllib.parse import quote

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=" + quote(frappe.request.path)
        raise frappe.Redirect
    from thinknxg_ess_portal.api.bootstrap import get_boot
    from thinknxg_ess_portal.services.identity import settings
    boot = get_boot()
    s = settings()
    context.no_cache = 1
    context.boot_json = frappe.as_json(boot, indent=None).replace("</", "<\\/")
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.portal_title = s.portal_title or "thinkNXG ESS Portal"
    context.theme_color = s.pwa_theme_color or s.brand_color or "#0F6E5A"
    context.lang = boot.get("lang") or "en"
    context.dir = "rtl" if context.lang == "ar" else "ltr"
    return context
