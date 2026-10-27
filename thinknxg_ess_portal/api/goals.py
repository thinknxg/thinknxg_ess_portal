import frappe
from frappe import _
from frappe.utils import flt, today
from thinknxg_ess_portal.api._guard import guard
from thinknxg_ess_portal.services.idempotency import run_once


def _exists(dt):
    return frappe.db.exists("DocType", dt)


@frappe.whitelist(methods=["GET"])
def overview():
    emp = guard("enable_goals")
    out = {"goals": [], "appraisals": [], "feedback_count": 0, "training": [], "onboarding": None}
    if _exists("Goal"):
        meta = frappe.get_meta("Goal")
        fields = [f for f in ("name", "goal_name", "progress", "status", "start_date", "end_date", "appraisal_cycle",
                              "kra", "parent_goal", "is_group", "description") if f == "name" or meta.has_field(f)]
        out["goals"] = frappe.get_all("Goal", filters={"employee": emp.name}, fields=fields, order_by="end_date asc")
    if _exists("Appraisal"):
        meta = frappe.get_meta("Appraisal")
        fields = [f for f in ("name", "appraisal_cycle", "final_score", "status", "docstatus", "total_score",
                              "avg_feedback_score", "self_score") if f == "name" or meta.has_field(f)]
        out["appraisals"] = frappe.get_all("Appraisal", filters={"employee": emp.name}, fields=fields,
                                           order_by="creation desc", limit=6)
    if _exists("Employee Performance Feedback"):
        out["feedback_count"] = frappe.db.count("Employee Performance Feedback", {"employee": emp.name, "docstatus": 1})
    if _exists("Training Event Employee"):
        out["training"] = frappe.db.sql("""select te.name, te.event_name, te.start_time, te.end_time, te.location,
                te.event_status, tee.status attendee_status from `tabTraining Event` te
                join `tabTraining Event Employee` tee on tee.parent=te.name where tee.employee=%s and te.docstatus<2
                order by te.start_time desc limit 20""", emp.name, as_dict=True)
    if _exists("Employee Onboarding"):
        ob = frappe.get_all("Employee Onboarding", filters={"employee": emp.name, "docstatus": ["<", 2]},
                            fields=["name", "boarding_status"], limit=1)
        if ob:
            acts = frappe.get_all("Employee Boarding Activity", filters={"parent": ob[0].name},
                                  fields=["activity_name", "user", "required_for_employee_creation", "task"])
            done = 0
            for a in acts:
                a["completed"] = bool(a.task and frappe.db.get_value("Task", a.task, "status") == "Completed")
                done += a["completed"]
            out["onboarding"] = {"name": ob[0].name, "status": ob[0].boarding_status, "activities": acts,
                                 "progress": round(100 * done / len(acts)) if acts else 0}
    return out


@frappe.whitelist(methods=["POST"])
def update_goal_progress(name, progress, client_request_id=None):
    emp = guard("enable_goals")
    goal = frappe.get_doc("Goal", name)
    if goal.employee != emp.name or goal.get("is_group"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    if goal.get("appraisal_cycle") and frappe.db.get_value("Appraisal Cycle", goal.appraisal_cycle, "status") == "Completed":
        frappe.throw(_("The appraisal cycle is closed."))
    p = max(0.0, min(flt(progress), 100.0))

    def do():
        goal.progress = p
        goal.flags.ignore_permissions = True
        goal.save()
        return {"doctype": "Goal", "name": goal.name, "progress": p}

    return run_once(client_request_id, "goal_progress", do)
