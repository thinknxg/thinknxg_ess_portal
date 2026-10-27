import frappe
from frappe import _
from frappe.utils import today, getdate, cint
from thinknxg_ess_portal.api._guard import guard, parse
from thinknxg_ess_portal.services import identity, workflow
from thinknxg_ess_portal.services.idempotency import run_once


def _require_approver():
    guard(employee=False)
    if not (identity.is_manager() or identity.is_hr() or workflow.delegators(frappe.session.user, "include_leave")
            or workflow.delegators(frappe.session.user, "include_expense")
            or frappe.get_all("Has Role", filters={"parent": frappe.session.user,
                                                   "role": ["in", ["Leave Approver", "Expense Approver"]]}, limit=1)):
        frappe.throw(_("Approvals are available to managers and HR."), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def get_pending(types=None):
    _require_approver()
    items = workflow.pending(types=parse(types))
    counts = {}
    for i in items:
        counts[i["type"]] = counts.get(i["type"], 0) + 1
    return {"items": items, "counts": counts}


@frappe.whitelist(methods=["GET"])
def get_detail(doctype, name):
    _require_approver()
    items = {(i["doctype"], i["name"]): i for i in workflow.pending(types=[workflow.TYPES[doctype]["key"]])} \
        if doctype in workflow.TYPES else {}
    item = items.get((doctype, name))
    if not item:
        frappe.throw(_("Not found"), frappe.DoesNotExistError)
    out = dict(item)
    emp = item["employee"]
    if doctype == "Leave Application":
        from thinknxg_ess_portal.api.leave import _balances
        out["balances"] = _balances(emp)
        d = item["details"]
        peers = [e for e in identity.team_employees() if e != emp] or [""]
        out["team_overlap"] = frappe.get_all("Leave Application", filters=[
            ["employee", "in", peers], ["docstatus", "<", 2], ["status", "in", ["Open", "Approved"]],
            ["from_date", "<=", d["to_date"]], ["to_date", ">=", d["from_date"]]],
            fields=["employee_name", "from_date", "to_date", "status"], limit=10)
    if doctype == "Expense Claim":
        doc = frappe.get_doc("Expense Claim", name)
        out["lines"] = [{"date": r.expense_date, "type": r.expense_type, "description": r.description,
                         "amount": r.amount} for r in doc.expenses]
        out["attachments"] = frappe.get_all("File", filters={"attached_to_doctype": "Expense Claim",
                                                            "attached_to_name": name}, fields=["file_name", "file_url"])
    out["timeline"] = frappe.get_all("Version", filters={"ref_doctype": doctype, "docname": name},
                                     fields=["owner", "creation"], order_by="creation asc", limit=20)
    return out


@frappe.whitelist(methods=["POST"])
def act(doctype, name, action, comment=None, client_request_id=None):
    _require_approver()
    return run_once(client_request_id, f"approval_{action}",
                    lambda: workflow.act(doctype, name, action, comment))


@frappe.whitelist(methods=["POST"])
def bulk_act(items, action, comment=None):
    _require_approver()
    results = []
    for it in parse(items, [])[:50]:
        try:
            frappe.db.savepoint("ess_bulk")
            results.append({**workflow.act(it["doctype"], it["name"], action, comment), "ok": True})
        except Exception as e:
            frappe.db.rollback(save_point="ess_bulk")
            frappe.local.message_log = []
            results.append({"doctype": it.get("doctype"), "name": it.get("name"), "ok": False, "error": str(e)[:200]})
    return {"results": results}


@frappe.whitelist(methods=["GET"])
def history(limit=30):
    _require_approver()
    return frappe.get_all("ESS Audit Event", filters={"event_type": "Approval", "user": frappe.session.user},
                          fields=["reference_doctype", "reference_name", "details", "creation"],
                          order_by="creation desc", limit=min(cint(limit) or 30, 100))


@frappe.whitelist(methods=["GET"])
def list_delegations():
    guard(employee=False)
    u = frappe.session.user
    return frappe.get_all("ESS Approval Delegation", filters=[["delegator", "=", u]],
                          or_filters=None, fields=["name", "delegator", "delegate", "from_date", "to_date",
                                                   "include_leave", "include_expense", "include_attendance",
                                                   "is_active", "reason"], order_by="from_date desc") + \
        frappe.get_all("ESS Approval Delegation", filters={"delegate": u, "is_active": 1},
                       fields=["name", "delegator", "delegate", "from_date", "to_date", "include_leave",
                               "include_expense", "include_attendance", "is_active", "reason"])


@frappe.whitelist(methods=["POST"])
def save_delegation(delegate, from_date, to_date, include_leave=1, include_expense=1, include_attendance=1,
                    reason=None, client_request_id=None):
    _require_approver()
    if not frappe.db.exists("Employee", {"user_id": delegate, "status": "Active"}):
        frappe.throw(_("Delegate must be an active employee"))
    if getdate(from_date) < getdate(today()):
        frappe.throw(_("Delegation cannot start in the past"))

    def do():
        doc = frappe.get_doc({"doctype": "ESS Approval Delegation", "delegator": frappe.session.user,
                              "delegate": delegate, "from_date": from_date, "to_date": to_date,
                              "include_leave": cint(include_leave), "include_expense": cint(include_expense),
                              "include_attendance": cint(include_attendance), "is_active": 1,
                              "reason": (reason or "")[:300]})
        doc.insert(ignore_permissions=True)
        from thinknxg_ess_portal.services.notifications import notify
        notify(delegate, "Approvals", _("{0} delegated approvals to you").format(
            frappe.utils.get_fullname(frappe.session.user)), f"{from_date} → {to_date}", "/ess/team/approvals",
               doc.doctype, doc.name)
        return {"doctype": doc.doctype, "name": doc.name}

    return run_once(client_request_id, "delegation", do)


@frappe.whitelist(methods=["POST"])
def revoke_delegation(name):
    guard(employee=False)
    doc = frappe.get_doc("ESS Approval Delegation", name)
    if doc.delegator != frappe.session.user and not identity.is_hr_manager():
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    doc.is_active = 0
    doc.save(ignore_permissions=True)
    return {"name": name, "revoked": True}


@frappe.whitelist(methods=["GET"])
def search_colleagues(txt=""):
    emp = guard()
    txt = (txt or "").strip()[:60]
    if len(txt) < 2:
        return []
    return frappe.get_all("Employee", filters={"status": "Active", "company": emp.company, "name": ["!=", emp.name],
                                               "user_id": ["is", "set"]},
                          or_filters={"employee_name": ["like", f"%{txt}%"], "name": ["like", f"%{txt}%"]},
                          fields=["name", "employee_name", "designation", "department", "image", "user_id"], limit=10)
