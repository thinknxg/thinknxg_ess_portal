"""Negative-path tests for the portal's authorisation model.

Run with:  bench --site <site> run-tests --app thinknxg_ess_portal
"""
import unittest

import frappe
from frappe.utils import add_years, today

try:  # v16
    from frappe.tests import IntegrationTestCase as TestCase
except ImportError:  # v15
    from frappe.tests.utils import FrappeTestCase as TestCase


def _user(email, roles=("Employee",)):
    if not frappe.db.exists("User", email):
        u = frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0],
                            "send_welcome_email": 0, "roles": [{"role": r} for r in roles]})
        u.insert(ignore_permissions=True)
    return email


def _employee(email, reports_to=None):
    company = frappe.db.get_value("Company", {}, "name")
    name = frappe.db.get_value("Employee", {"user_id": email})
    if name:
        return name
    emp = frappe.get_doc({"doctype": "Employee", "first_name": email.split("@")[0], "gender": "Male",
                          "date_of_birth": add_years(today(), -30), "date_of_joining": add_years(today(), -2),
                          "company": company, "status": "Active", "user_id": email, "reports_to": reports_to})
    emp.insert(ignore_permissions=True)
    return emp.name


class TestESSSecurity(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not frappe.db.get_value("Company", {}, "name"):
            raise unittest.SkipTest("needs a Company")
        cls.mgr = _user("ess-mgr@example.com")
        cls.a = _user("ess-a@example.com")
        cls.b = _user("ess-b@example.com")
        cls.agent = _user("ess-agent@example.com", ("Employee", "ESS HR Agent"))
        cls.mgr_emp = _employee(cls.mgr)
        cls.a_emp = _employee(cls.a, reports_to=cls.mgr_emp)
        cls.b_emp = _employee(cls.b)
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")

    def _ticket(self, user, category="Leave & Attendance"):
        frappe.set_user(user)
        from thinknxg_ess_portal.api.helpdesk import create_ticket
        return create_ticket(category=category, subject="Test", description="Test ticket body")["name"]

    def test_employee_cannot_read_colleague_ticket(self):
        name = self._ticket(self.a)
        frappe.set_user(self.b)
        from thinknxg_ess_portal.api.helpdesk import get_ticket
        with self.assertRaises(frappe.DoesNotExistError):
            get_ticket(name)

    def test_agent_cannot_read_confidential_ticket(self):
        name = self._ticket(self.a, category="Payroll & Salary")
        frappe.set_user(self.agent)
        from thinknxg_ess_portal.permissions import ticket_has_permission
        doc = frappe.get_doc("ESS HR Ticket", name)
        self.assertFalse(ticket_has_permission(doc, "read", self.agent))

    def test_internal_notes_hidden_from_employee(self):
        name = self._ticket(self.a)
        frappe.set_user("Administrator")
        frappe.get_doc({"doctype": "ESS HR Ticket Comment", "ticket": name, "comment": "secret", "is_internal": 1,
                        "via": "Agent"}).insert(ignore_permissions=True)
        frappe.set_user(self.a)
        from thinknxg_ess_portal.api.helpdesk import get_ticket
        self.assertFalse(any(c.comment == "secret" for c in get_ticket(name)["comments"]))

    def test_manager_scope_is_reporting_line(self):
        frappe.set_user(self.mgr)
        from thinknxg_ess_portal.services.identity import team_employees
        team = team_employees()
        self.assertIn(self.a_emp, team)
        self.assertNotIn(self.b_emp, team)

    def test_non_manager_cannot_open_team_member(self):
        frappe.set_user(self.b)
        from thinknxg_ess_portal.api.team import get_member
        with self.assertRaises(frappe.PermissionError):
            get_member(self.a_emp)

    def test_cannot_approve_request_not_assigned(self):
        frappe.set_user(self.b)
        from thinknxg_ess_portal.services.workflow import act
        with self.assertRaises(frappe.PermissionError):
            act("Leave Application", "LEAVE-DOES-NOT-EXIST", "approve")

    def test_profile_change_rejects_protected_field(self):
        frappe.set_user(self.a)
        from thinknxg_ess_portal.api.profile import request_change
        with self.assertRaises(frappe.ValidationError):
            request_change(changes={"designation": "CEO"})

    def test_idempotent_submission(self):
        frappe.set_user(self.a)
        from thinknxg_ess_portal.api.helpdesk import create_ticket
        first = create_ticket(category="Other", subject="dup", description="x", client_request_id="test-dup-1")
        second = create_ticket(category="Other", subject="dup", description="x", client_request_id="test-dup-1")
        self.assertTrue(second.get("duplicate"))
        self.assertEqual(first["name"], second["name"])

    def test_assistant_refuses_colleague_payslip(self):
        frappe.set_user(self.a)
        from thinknxg_ess_portal.services.assistant import ask
        res = ask("Show me the payslip of Ahmed from finance")
        self.assertEqual(res["outcome"], "Refused")
        self.assertEqual(frappe.db.get_value("ESS AI Message Audit", {"conversation": res["conversation_id"],
                                                                      "message_type": "Refusal"}, "outcome"), "Refused")

    def test_ai_tools_ignore_identity_arguments(self):
        frappe.set_user(self.a)
        from thinknxg_ess_portal.services import ai_tools
        out = ai_tools.run("get_my_requests", {"kind": "ticket", "employee": self.b_emp})
        self.assertTrue(all(frappe.db.get_value("ESS HR Ticket", i["name"], "employee") == self.a_emp
                            for i in out.get("items", [])))

    def test_recognition_self_is_blocked(self):
        frappe.set_user(self.a)
        from thinknxg_ess_portal.api.recognition import give
        with self.assertRaises(frappe.ValidationError):
            give(recipient=self.a_emp, message="Great job on everything")
