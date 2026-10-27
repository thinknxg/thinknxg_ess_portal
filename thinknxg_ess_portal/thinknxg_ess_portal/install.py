import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

ROLES = {
    "ESS Portal Admin": "Configures the ESS portal, AI sources and templates",
    "ESS HR Agent": "Works HR helpdesk tickets",
    "ESS Payroll Officer": "Handles payroll-related tickets and confidential categories",
    "ESS Department Head": "Approves and sees aggregates for departments they head",
}

TICKET_CATEGORIES = [
    ("Leave & Attendance", "🗓️", 4, 24, 0), ("Payroll & Salary", "💰", 4, 48, 1),
    ("Benefits & Insurance", "🩺", 8, 72, 0), ("Documents & Letters", "📄", 4, 24, 0),
    ("Visa & Residency", "🛂", 8, 72, 0), ("IT Access", "💻", 2, 8, 0), ("Other", "💬", 8, 72, 0),
]
RECOGNITION = [
    ("Customer First", "🤝", 10), ("Teamwork", "🙌", 10), ("Innovation", "💡", 15),
    ("Ownership", "🎯", 10), ("Going the Extra Mile", "🚀", 15),
]
BADGES = [
    ("First Year", "🎂", "Work Anniversary", 1), ("Five Years", "🏆", "Work Anniversary", 5),
    ("Team Player", "🙌", "Recognitions Received", 5), ("Appreciator", "💐", "Recognitions Given", 10),
    ("Lifelong Learner", "📚", "Training Completed", 3), ("Policy Champion", "🛡️", "Policies Acknowledged", 3),
    ("Onboarded", "✅", "Onboarding Completed", 1),
]

EMPLOYMENT_LETTER = """<div style="font-family: Inter, Arial, sans-serif; font-size: 13px; line-height: 1.6;">
<p style="text-align:right">{{ frappe.utils.formatdate(today) }}</p>
{% if addressed_to %}<p>To: {{ addressed_to }}</p>{% else %}<p>To whom it may concern,</p>{% endif %}
<h3 style="text-align:center">EMPLOYMENT VERIFICATION</h3>
<p>This is to certify that <b>{{ employee.salutation or "" }} {{ employee.employee_name }}</b>
(Employee ID {{ employee.name }}) has been employed with <b>{{ company.company_name }}</b>
since {{ frappe.utils.formatdate(employee.date_of_joining) }} and currently holds the position of
<b>{{ employee.designation or "-" }}</b> in the {{ employee.department or "-" }} department.</p>
{% if salary %}<p>Monthly gross salary: <b>{{ salary.currency }} {{ frappe.utils.fmt_money(salary.gross_pay) }}</b>.</p>{% endif %}
{% if purpose %}<p>This letter is issued at the employee's request for the purpose of: {{ purpose }}.</p>{% endif %}
<p>This letter carries no liability on the part of the company.</p>
<br><p>{{ signatory.name or "" }}<br>{{ signatory.designation or "" }}</p>
<p style="font-size:10px;color:#666">Verification code: {{ verification_code }}{% if verify_url %} - verify at {{ verify_url }}{% endif %}</p>
</div>"""


def after_install():
    after_migrate()


def after_migrate():
    _roles()
    _custom_fields()
    _settings()
    _seed()
    frappe.db.commit()


def _roles():
    for role, desc in ROLES.items():
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1,
                            "description": desc}).insert(ignore_permissions=True)


def _custom_fields():
    create_custom_fields({
        "Department": [{
            "fieldname": "ess_department_head", "label": "ESS Department Head", "fieldtype": "Link",
            "options": "User", "insert_after": "department_name",
            "description": "Gets manager-level visibility of this department (and sub-departments) in the ESS portal",
        }],
        # Attendance Request has no native rejection state; the portal records it here.
        "Attendance Request": [
            {"fieldname": "ess_status", "label": "ESS Review Status", "fieldtype": "Select",
             "options": "Pending\nRejected", "default": "Pending", "insert_after": "explanation",
             "read_only": 1, "in_standard_filter": 1},
            {"fieldname": "ess_review_comment", "label": "ESS Review Comment", "fieldtype": "Small Text",
             "insert_after": "ess_status", "read_only": 1},
        ],
    }, ignore_validate=True, update=True)


def _settings():
    s = frappe.get_single("ESS Portal Settings")
    if not s.portal_title:
        s.portal_title = "thinkNXG ESS Portal"
        s.flags.ignore_mandatory = True
        s.save(ignore_permissions=True)


def _seed():
    for name, icon, fr, res, conf in TICKET_CATEGORIES:
        if not frappe.db.exists("ESS HR Ticket Category", name):
            frappe.get_doc({"doctype": "ESS HR Ticket Category", "category_name": name, "icon": icon,
                            "first_response_hours": fr, "resolution_hours": res,
                            "is_confidential": conf, "visible_to_employees": 1}).insert(ignore_permissions=True)
    for name, icon, pts in RECOGNITION:
        if not frappe.db.exists("ESS Recognition Category", name):
            frappe.get_doc({"doctype": "ESS Recognition Category", "category_name": name, "icon": icon,
                            "default_points": pts, "is_active": 1}).insert(ignore_permissions=True)
    for name, icon, rule, threshold in BADGES:
        if not frappe.db.exists("ESS Badge", name):
            frappe.get_doc({"doctype": "ESS Badge", "badge_name": name, "icon": icon, "rule_type": rule,
                            "threshold": threshold, "is_active": 1}).insert(ignore_permissions=True)
    if not frappe.db.exists("ESS Document Template", "Employment Verification Letter"):
        frappe.get_doc({"doctype": "ESS Document Template", "template_name": "Employment Verification Letter",
                        "template_key": "employment_verification", "document_type": "Employment Verification",
                        "is_active": 1, "visible_to_employees": 1, "requires_purpose": 1,
                        "max_per_month": 3, "template_html": EMPLOYMENT_LETTER}).insert(ignore_permissions=True)
    if not frappe.db.exists("ESS Document Template", "Salary Certificate"):
        frappe.get_doc({"doctype": "ESS Document Template", "template_name": "Salary Certificate",
                        "template_key": "salary_certificate", "document_type": "Salary Certificate",
                        "is_active": 1, "visible_to_employees": 1, "requires_purpose": 1, "requires_approval": 1,
                        "approver_role": "HR Manager", "include_salary": 1, "addressee_required": 1,
                        "max_per_month": 2, "min_service_months": 3,
                        "template_html": EMPLOYMENT_LETTER.replace("EMPLOYMENT VERIFICATION", "SALARY CERTIFICATE")
                        }).insert(ignore_permissions=True)
