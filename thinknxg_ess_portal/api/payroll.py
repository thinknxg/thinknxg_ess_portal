import frappe
from frappe import _
from frappe.utils import getdate, flt
from thinknxg_ess_portal.api._guard import guard
from thinknxg_ess_portal.services import identity
from thinknxg_ess_portal.services.audit import log_event

LIST_FIELDS = ["name", "start_date", "end_date", "posting_date", "gross_pay", "total_deduction", "net_pay",
               "currency", "payment_days", "status"]


def _authorised_slip(name):
    emp = identity.get_employee(required=False)
    slip = frappe.db.get_value("Salary Slip", name, ["name", "employee", "docstatus"], as_dict=True)
    if not slip or slip.docstatus != 1:
        frappe.throw(_("Payslip not found"), frappe.DoesNotExistError)
    if emp and slip.employee == emp.name:
        return slip, False
    if identity.is_payroll_officer() or "HR Manager" in identity.roles():
        log_event("Sensitive Access", "Salary Slip", name, employee=slip.employee, details="payslip viewed by payroll/HR")
        return slip, True
    frappe.throw(_("Payslip not found"), frappe.DoesNotExistError)  # do not reveal existence


@frappe.whitelist(methods=["GET"])
def list_payslips(year=None):
    emp = guard("enable_payroll")
    flt_ = {"employee": emp.name, "docstatus": 1}
    if year:
        flt_["end_date"] = ["between", [f"{int(year)}-01-01", f"{int(year)}-12-31"]]
    rows = frappe.get_all("Salary Slip", filters=flt_, fields=LIST_FIELDS, order_by="end_date desc", limit=60)
    years = sorted({getdate(r.end_date).year for r in frappe.get_all(
        "Salary Slip", filters={"employee": emp.name, "docstatus": 1}, fields=["end_date"])}, reverse=True)
    return {"payslips": rows, "years": years}


@frappe.whitelist(methods=["GET"])
def get_payslip(name):
    guard("enable_payroll", employee=False)
    slip, _other = _authorised_slip(name)
    doc = frappe.get_doc("Salary Slip", name)
    year_start = f"{getdate(doc.end_date).year}-01-01"
    ytd = frappe.db.sql("""select sum(gross_pay) gross, sum(total_deduction) ded, sum(net_pay) net
        from `tabSalary Slip` where employee=%s and docstatus=1 and end_date between %s and %s""",
                        (doc.employee, year_start, doc.end_date), as_dict=True)[0]
    return {
        **{f: doc.get(f) for f in LIST_FIELDS}, "employee_name": doc.employee_name,
        "designation": doc.get("designation"), "department": doc.get("department"),
        "absent_days": doc.get("absent_days"), "total_working_days": doc.get("total_working_days"),
        "leave_without_pay": doc.get("leave_without_pay"),
        "earnings": [{"component": r.salary_component, "amount": flt(r.amount, 2)} for r in doc.earnings if r.amount],
        "deductions": [{"component": r.salary_component, "amount": flt(r.amount, 2)} for r in doc.deductions if r.amount],
        "ytd": {"gross": flt(ytd.gross, 2), "deductions": flt(ytd.ded, 2), "net": flt(ytd.net, 2)},
    }


@frappe.whitelist(methods=["GET"])
def download_payslip(name):
    guard("enable_payroll", employee=False)
    slip, _other = _authorised_slip(name)
    pdf = frappe.get_print("Salary Slip", name, as_pdf=True)
    log_event("Download", "Salary Slip", name, employee=slip.employee, details="payslip pdf")
    frappe.local.response.filename = f"Payslip-{name}.pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "pdf"


@frappe.whitelist(methods=["GET"])
def get_benefits():
    emp = guard("enable_payroll")
    out = {"applications": [], "ledger": [], "additional_salary": []}
    if frappe.db.exists("DocType", "Employee Benefit Application"):
        out["applications"] = frappe.get_all("Employee Benefit Application", filters={"employee": emp.name, "docstatus": 1},
                                             fields=["name", "date", "payroll_period", "max_benefits",
                                                     "remaining_benefit"], order_by="date desc", limit=10)
    if frappe.db.exists("DocType", "Employee Benefit Ledger"):
        meta = frappe.get_meta("Employee Benefit Ledger")
        fields = [f for f in ("name", "salary_component", "amount", "transaction_type", "posting_date", "payroll_period")
                  if f == "name" or meta.has_field(f)]
        out["ledger"] = frappe.get_all("Employee Benefit Ledger", filters={"employee": emp.name}, fields=fields,
                                       order_by="creation desc", limit=50)
    out["additional_salary"] = frappe.get_all("Additional Salary", filters={"employee": emp.name, "docstatus": 1},
                                              fields=["name", "salary_component", "amount", "payroll_date", "type"],
                                              order_by="payroll_date desc", limit=20)
    return out
