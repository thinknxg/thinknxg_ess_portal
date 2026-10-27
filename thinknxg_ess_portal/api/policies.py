import frappe
from frappe import _
from frappe.utils import now_datetime, add_days, getdate, today
from thinknxg_ess_portal.api._guard import guard
from thinknxg_ess_portal.api.announcements import audience_condition


def _visible_policies(emp):
    vals = {"company": emp.company, "department": emp.department or "", "branch": emp.get("branch") or "",
            "designation": emp.designation or ""}
    return frappe.db.sql(f"""select a.name, a.policy_title, a.policy_code, a.version, a.effective_date,
            a.requires_acknowledgement, a.acknowledgement_due_days, a.attachment, a.creation
        from `tabESS Policy` a where a.is_active=1 and {audience_condition(emp)}
        order by a.effective_date desc""", vals, as_dict=True)


def _pending_for(emp):
    acked = set(frappe.get_all("ESS Policy Acknowledgement", filters={"employee": emp.name}, pluck="policy"))
    out = []
    for p in _visible_policies(emp):
        if p.requires_acknowledgement and p.name not in acked:
            start = p.effective_date or getdate(p.creation)
            due = add_days(start, p.acknowledgement_due_days or 14)
            out.append({**p, "due_date": str(due), "overdue": getdate(due) < getdate(today())})
    return out


@frappe.whitelist(methods=["GET"])
def list_mine():
    emp = guard()
    acks = {a.policy: a for a in frappe.get_all("ESS Policy Acknowledgement", filters={"employee": emp.name},
                                                fields=["policy", "acknowledged_on", "policy_version"])}
    pending = {p["name"]: p for p in _pending_for(emp)}
    out = []
    for p in _visible_policies(emp):
        a = acks.get(p.name)
        out.append({**p, "acknowledged_on": a.acknowledged_on if a else None,
                    "status": "Acknowledged" if a else ("Overdue" if pending.get(p.name, {}).get("overdue") else
                                                         "Pending" if p.name in pending else "Info"),
                    "due_date": pending.get(p.name, {}).get("due_date")})
    return out


@frappe.whitelist(methods=["GET"])
def get_policy(name):
    emp = guard()
    if not any(p.name == name for p in _visible_policies(emp)):
        frappe.throw(_("Not found"), frappe.DoesNotExistError)
    p = frappe.get_doc("ESS Policy", name)
    return {"name": p.name, "policy_title": p.policy_title, "version": p.version, "content": p.content,
            "effective_date": p.effective_date, "attachment": p.attachment,
            "requires_acknowledgement": p.requires_acknowledgement,
            "acknowledged": bool(frappe.db.exists("ESS Policy Acknowledgement", {"employee": emp.name, "policy": name}))}


@frappe.whitelist(methods=["POST"])
def acknowledge(name):
    emp = guard()
    if not any(p.name == name for p in _visible_policies(emp)):
        frappe.throw(_("Not found"), frappe.DoesNotExistError)
    if frappe.db.exists("ESS Policy Acknowledgement", {"employee": emp.name, "policy": name}):
        return {"ok": True, "duplicate": True}
    ua = frappe.get_request_header("User-Agent") if getattr(frappe.local, "request", None) else None
    frappe.get_doc({"doctype": "ESS Policy Acknowledgement", "policy": name, "employee": emp.name,
                    "user": frappe.session.user, "acknowledged_on": now_datetime(),
                    "ip_address": getattr(frappe.local, "request_ip", None), "user_agent": (ua or "")[:500]
                    }).insert(ignore_permissions=True)
    return {"ok": True}
