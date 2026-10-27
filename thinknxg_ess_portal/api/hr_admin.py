import frappe
from frappe import _
from frappe.utils import cint, today, add_days
from thinknxg_ess_portal.api._guard import guard, parse
from thinknxg_ess_portal.services import identity
from thinknxg_ess_portal.services.audit import log_event

EDITABLE_SETTINGS = [
    "portal_title", "brand_color", "default_language", "support_email", "weekend_days",
    "enable_attendance", "enable_checkin", "enable_leave", "enable_payroll", "enable_expenses", "enable_helpdesk",
    "enable_documents", "enable_recognition", "enable_assistant", "enable_goals", "enable_analytics",
    "require_geolocation", "allow_checkin_without_shift", "checkin_cooldown_minutes", "show_team_availability",
    "auto_submit_approved_expenses", "default_ticket_assignee", "allow_reopen_days", "auto_close_resolved_days",
    "public_verification", "document_rate_limit_per_day", "document_expiry_alert_days",
    "recognition_requires_approval", "allow_public_recognition", "monthly_points_budget", "min_group_size",
    "ai_provider", "ai_model", "ai_base_url", "ai_allow_salary_answers", "ai_max_requests_per_hour",
    "ai_retention_days", "ai_system_notice", "pwa_theme_color",
]


def _hr():
    guard(employee=False)
    if not identity.is_hr():
        frappe.throw(_("HR operations are restricted."), frappe.PermissionError)


def _admin():
    guard(employee=False)
    if not identity.is_admin():
        frappe.throw(_("Portal configuration is restricted to ESS Portal Admins."), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def employee_search(q=None, department=None, limit=30):
    _hr()
    scope = identity.hr_scope_employees()
    flt = {"status": "Active"}
    if scope is not None:
        flt["name"] = ["in", scope or [""]]
    if department:
        flt["department"] = department
    or_f = {"employee_name": ["like", f"%{q[:60]}%"], "name": ["like", f"%{q[:60]}%"]} if q else None
    return frappe.get_all("Employee", filters=flt, or_filters=or_f, limit=min(cint(limit) or 30, 100),
                          fields=["name", "employee_name", "designation", "department", "branch", "image",
                                  "date_of_joining", "company"], order_by="employee_name asc")


@frappe.whitelist(methods=["GET"])
def employee_detail(employee):
    _hr()
    scope = identity.hr_scope_employees()
    if scope is not None and employee not in scope:
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    meta = frappe.get_meta("Employee")
    fields = [f for f in ("name", "employee_name", "designation", "department", "branch", "company", "date_of_joining",
                          "employment_type", "reports_to", "company_email", "cell_number", "image", "status",
                          "nationality") if f == "name" or meta.has_field(f)]
    data = frappe.db.get_value("Employee", employee, fields, as_dict=True)
    log_event("Sensitive Access", "Employee", employee, employee=employee, details="HR employee lookup")
    data["documents"] = frappe.get_all("ESS Employee Document", filters={"employee": employee},
                                       fields=["name", "document_type", "document_number", "expiry_date", "verified"])
    data["open_tickets"] = frappe.db.count("ESS HR Ticket", {"employee": employee,
                                                             "status": ["not in", ["Resolved", "Closed"]]})
    data["pending_changes"] = frappe.get_all("ESS Profile Change Request", filters={"employee": employee, "status": "Pending"},
                                             pluck="name")
    from thinknxg_ess_portal.api.leave import _balances
    try:
        data["balances"] = _balances(employee)
    except Exception:
        data["balances"] = []
    return data


@frappe.whitelist(methods=["POST"])
def verify_document(name, verified=1):
    _hr()
    doc = frappe.get_doc("ESS Employee Document", name)
    doc.verified = cint(verified)
    doc.verified_by = frappe.session.user
    doc.save(ignore_permissions=True)
    return {"name": name, "verified": doc.verified}


@frappe.whitelist(methods=["GET"])
def expiring_documents(days=60):
    _hr()
    scope = identity.hr_scope_employees()
    flt = {"expiry_date": ["between", [add_days(today(), -30), add_days(today(), min(cint(days) or 60, 365))]]}
    if scope is not None:
        flt["employee"] = ["in", scope or [""]]
    return frappe.get_all("ESS Employee Document", filters=flt, order_by="expiry_date asc", limit=500,
                          fields=["name", "employee", "employee_name", "document_type", "document_number",
                                  "expiry_date", "verified", "reminder_sent_on"])


@frappe.whitelist(methods=["GET"])
def get_settings():
    _admin()
    s = frappe.get_single("ESS Portal Settings")
    out = {k: s.get(k) for k in EDITABLE_SETTINGS}
    out["ai_api_key_set"] = bool(s.get_password("ai_api_key", raise_exception=False))
    out["knowledge_sources"] = frappe.get_all("ESS Knowledge Source", fields=["name", "title", "source_type", "audience",
                                                                              "is_active", "chunk_count",
                                                                              "last_indexed_on"])
    return out


@frappe.whitelist(methods=["POST"])
def save_settings(values, ai_api_key=None):
    _admin()
    values = parse(values, {})
    s = frappe.get_single("ESS Portal Settings")
    changed = []
    for k, v in values.items():
        if k in EDITABLE_SETTINGS and s.get(k) != v:
            s.set(k, v)
            changed.append(k)
    if ai_api_key:
        s.ai_api_key = ai_api_key
        changed.append("ai_api_key")
    s.save(ignore_permissions=True)
    log_event("Settings Change", s.doctype, s.name, details="changed: " + ", ".join(changed))
    return {"ok": True, "changed": changed}


@frappe.whitelist(methods=["POST"])
def save_knowledge_source(title, content, source_type="Policy", audience="All Employees", is_active=1, name=None,
                          attachment=None):
    _admin()
    doc = frappe.get_doc("ESS Knowledge Source", name) if name else frappe.new_doc("ESS Knowledge Source")
    doc.update({"title": title, "content": frappe.utils.sanitize_html(content or ""), "source_type": source_type,
                "audience": audience, "is_active": cint(is_active), "attachment": attachment})
    doc.save(ignore_permissions=True)
    return {"name": doc.name}


@frappe.whitelist(methods=["GET"])
def audit_events(event_type=None, limit=100):
    _admin()
    flt = {"event_type": event_type} if event_type else {}
    return frappe.get_all("ESS Audit Event", filters=flt, order_by="creation desc", limit=min(cint(limit) or 100, 500),
                          fields=["event_type", "user", "employee", "reference_doctype", "reference_name", "details",
                                  "creation"])


@frappe.whitelist(methods=["GET"])
def ai_quality():
    _admin()
    return {
        "by_outcome": frappe.db.sql("""select outcome, count(*) n from `tabESS AI Message Audit`
            where creation>=%s group by outcome""", add_days(today(), -30), as_dict=True),
        "feedback": frappe.db.sql("""select feedback, count(*) n from `tabESS AI Message Audit`
            where creation>=%s and ifnull(feedback,'')!='' group by feedback""", add_days(today(), -30), as_dict=True),
        "avg_latency_ms": frappe.db.sql("""select avg(latency_ms) from `tabESS AI Message Audit`
            where creation>=%s and latency_ms>0""", add_days(today(), -30))[0][0],
    }
