"""Native HRMS document events -> portal notifications. Read-only reactions; no HR data is modified."""
import frappe
from frappe import _
from thinknxg_ess_portal.services.notifications import notify


def _user(employee):
    return frappe.db.get_value("Employee", employee, "user_id")


def on_leave_update(doc, method=None):
    before = doc.get_doc_before_save()
    if doc.status != "Open" and (not before or before.status != doc.status or method == "on_submit"):
        notify(_user(doc.employee), "Leave", _("Leave {0}").format(_(doc.status)),
               f"{doc.leave_type}: {doc.from_date} → {doc.to_date}", "/ess/leave", doc.doctype, doc.name)
    if method == "on_update" and not before and doc.leave_approver:
        notify(doc.leave_approver, "Approvals", _("Leave request from {0}").format(doc.employee_name),
               f"{doc.leave_type}: {doc.from_date} → {doc.to_date}", "/ess/team/approvals", doc.doctype, doc.name)


def on_expense_update(doc, method=None):
    before = doc.get_doc_before_save()
    if before and before.approval_status != doc.approval_status:
        notify(_user(doc.employee), "Expenses", _("Expense claim {0}").format(_(doc.approval_status)),
               doc.name, "/ess/finances/expenses", doc.doctype, doc.name)
    if not before and doc.expense_approver:
        notify(doc.expense_approver, "Approvals", _("Expense claim from {0}").format(doc.employee_name),
               doc.name, "/ess/team/approvals", doc.doctype, doc.name)


def on_attendance_request_update(doc, method=None):
    if method == "on_submit":
        notify(_user(doc.employee), "Attendance", _("Attendance correction approved"),
               f"{doc.from_date} → {doc.to_date}", "/ess/attendance/corrections", doc.doctype, doc.name)


def on_salary_slip_submit(doc, method=None):
    notify(_user(doc.employee), "Payroll", _("Your payslip is ready"),
           f"{doc.start_date} → {doc.end_date}", f"/ess/finances/payslips/{doc.name}", doc.doctype, doc.name)


def on_announcement_update(doc, method=None):
    before = doc.get_doc_before_save()
    if doc.is_published and (not before or not before.is_published):
        frappe.publish_realtime("ess_announcement", {"name": doc.name, "title": doc.title}, after_commit=True)
