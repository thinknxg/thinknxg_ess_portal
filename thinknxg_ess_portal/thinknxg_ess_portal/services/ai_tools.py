"""Allow-listed assistant tools.

Design rule: NO tool accepts an employee, user or document-owner argument. Every tool resolves the
subject from the authenticated session, so the model cannot be talked into fetching a colleague's data.
Consequential actions are only *proposed*; the employee must confirm in the UI.
"""
import frappe
from frappe import _
from frappe.utils import today, add_days, getdate, cint
from thinknxg_ess_portal.services import identity, hrms
from thinknxg_ess_portal.services.ai_retrieval import search

TOOLS = [
    {"name": "search_policies", "description": "Search approved HR policies, handbooks and FAQs. Use for any policy or process question.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_my_leave_balances", "description": "Current leave balances of the signed-in employee.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "get_my_requests", "description": "Status of the signed-in employee's own recent requests.",
     "parameters": {"type": "object", "properties": {"kind": {"type": "string",
                    "enum": ["leave", "expense", "attendance", "ticket", "document"]}}, "required": ["kind"]}},
    {"name": "get_upcoming_holidays", "description": "Upcoming holidays from the employee's holiday list.",
     "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
    {"name": "get_my_latest_payslip", "description": "Latest payslip of the signed-in employee (amounts may be hidden by policy).",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "get_my_attendance_summary", "description": "Attendance counts for the signed-in employee in the current month.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "propose_leave_request", "description": "Prepare (NOT submit) a leave request for the employee to confirm.",
     "parameters": {"type": "object", "properties": {
         "leave_type": {"type": "string"}, "from_date": {"type": "string", "description": "YYYY-MM-DD"},
         "to_date": {"type": "string", "description": "YYYY-MM-DD"}, "half_day": {"type": "boolean"},
         "reason": {"type": "string"}}, "required": ["leave_type", "from_date", "to_date"]}},
    {"name": "propose_hr_ticket", "description": "Prepare (NOT submit) an HR helpdesk ticket for the employee to confirm.",
     "parameters": {"type": "object", "properties": {"category": {"type": "string"}, "subject": {"type": "string"},
                    "description": {"type": "string"}}, "required": ["subject", "description"]}},
]


def _emp():
    return identity.get_employee()


def search_policies(query, **_kw):
    hits = search(query, k=4)
    return {"results": [{"ref": f"[{i + 1}]", "title": h["title"], "section": h["heading"], "text": h["content"]}
                        for i, h in enumerate(hits)], "_citations": hits}


def get_my_leave_balances(**_kw):
    from thinknxg_ess_portal.api.leave import _balances
    return {"balances": _balances(_emp().name)}


def get_my_requests(kind="leave", **_kw):
    emp = _emp().name
    if kind == "leave":
        rows = frappe.get_all("Leave Application", filters={"employee": emp}, limit=5, order_by="creation desc",
                              fields=["name", "leave_type", "from_date", "to_date", "status"])
    elif kind == "expense":
        rows = frappe.get_all("Expense Claim", filters={"employee": emp}, limit=5, order_by="creation desc",
                              fields=["name", "posting_date", "total_claimed_amount", "approval_status", "status"])
    elif kind == "attendance":
        rows = frappe.get_all("Attendance Request", filters={"employee": emp}, limit=5, order_by="creation desc",
                              fields=["name", "from_date", "to_date", "reason", "docstatus"])
    elif kind == "ticket":
        rows = frappe.get_all("ESS HR Ticket", filters={"employee": emp}, limit=5, order_by="creation desc",
                              fields=["name", "subject", "status", "sla_status"])
    else:
        rows = frappe.get_all("ESS Document Request", filters={"employee": emp}, limit=5, order_by="creation desc",
                              fields=["name", "template", "status"])
    return {"kind": kind, "items": rows}


def get_upcoming_holidays(limit=5, **_kw):
    rows = hrms.holidays_between(_emp().name, today(), add_days(today(), 365))
    return {"holidays": [r for r in rows if not r.weekly_off][: max(1, min(cint(limit) or 5, 15))]}


def get_my_latest_payslip(**_kw):
    slip = frappe.get_all("Salary Slip", filters={"employee": _emp().name, "docstatus": 1}, limit=1,
                          order_by="end_date desc", fields=["name", "start_date", "end_date", "gross_pay",
                                                             "net_pay", "currency"])
    if not slip:
        return {"available": False}
    s = slip[0]
    out = {"available": True, "period": f"{s.start_date} to {s.end_date}", "link": f"/ess/finances/payslips/{s.name}"}
    if cint(identity.settings().get("ai_allow_salary_answers")):
        out.update({"gross_pay": s.gross_pay, "net_pay": s.net_pay, "currency": s.currency})
    else:
        out["amounts_hidden"] = True
    return out


def get_my_attendance_summary(**_kw):
    from frappe.utils import get_first_day
    rows = frappe.get_all("Attendance", filters={"employee": _emp().name, "docstatus": 1,
                                                 "attendance_date": [">=", get_first_day(today())]},
                          fields=["status", "count(name) as n"], group_by="status")
    return {"month": str(get_first_day(today()))[:7], "counts": {r.status: r.n for r in rows}}


def propose_leave_request(leave_type, from_date, to_date, half_day=False, reason="", **_kw):
    from thinknxg_ess_portal.api.leave import _preview
    preview = _preview(_emp(), leave_type, from_date, to_date, cint(half_day), from_date if half_day else None)
    payload = {"leave_type": leave_type, "from_date": str(getdate(from_date)), "to_date": str(getdate(to_date)),
               "half_day": cint(half_day), "half_day_date": str(getdate(from_date)) if half_day else None,
               "reason": (reason or "")[:500]}
    return {"proposal": {"type": "leave_request", "payload": payload, "preview": preview}}


def propose_hr_ticket(subject, description, category=None, **_kw):
    cats = frappe.get_all("ESS HR Ticket Category", filters={"visible_to_employees": 1}, pluck="name")
    if category not in cats:
        category = "Other" if "Other" in cats else (cats[0] if cats else None)
    return {"proposal": {"type": "hr_ticket", "payload": {"category": category, "subject": subject[:140],
                                                         "description": description[:4000]}}}


REGISTRY = {t["name"]: globals()[t["name"]] for t in TOOLS}


def run(name, args):
    fn = REGISTRY.get(name)
    if not fn:
        return {"error": "unknown tool"}
    if not isinstance(args, dict):
        args = {}
    # Defence in depth: strip any identity-like argument a model might invent.
    for k in list(args):
        if k in ("employee", "user", "user_id", "employee_id", "owner", "name"):
            args.pop(k)
    try:
        return fn(**args)
    except frappe.PermissionError:
        return {"error": "not permitted"}
    except Exception as e:
        frappe.local.message_log = []  # validation messages belong to the tool result, not the HTTP response
        return {"error": str(e)[:300]}
