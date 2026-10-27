import frappe
from frappe import _
from frappe.utils import cint
from thinknxg_ess_portal.api._guard import guard
from thinknxg_ess_portal.services import assistant


@frappe.whitelist(methods=["POST"])
def ask(message, conversation_id=None, lang="en"):
    guard("enable_assistant")
    return assistant.ask(message, conversation_id, lang)


@frappe.whitelist(methods=["POST"])
def confirm_action(token):
    guard("enable_assistant")
    return assistant.confirm(token)


@frappe.whitelist(methods=["POST"])
def feedback(conversation_id, helpful):
    guard("enable_assistant")
    owner = frappe.db.get_value("ESS AI Conversation", conversation_id, "user")
    if owner != frappe.session.user:
        frappe.throw(_("Not found"), frappe.DoesNotExistError)
    last = frappe.get_all("ESS AI Message Audit", filters={"conversation": conversation_id,
                                                           "message_type": ["in", ["Assistant Answer", "Action Proposal"]]},
                          pluck="name", order_by="creation desc", limit=1)
    if last:
        frappe.db.set_value("ESS AI Message Audit", last[0], "feedback", "Helpful" if cint(helpful) else "Not Helpful")
    return {"ok": True}


@frappe.whitelist(methods=["GET"])
def conversations():
    guard("enable_assistant")
    return frappe.get_all("ESS AI Conversation", filters={"user": frappe.session.user, "retention_status": "Active"},
                          fields=["name", "title", "last_message_on", "message_count"], order_by="last_message_on desc",
                          limit=20)


@frappe.whitelist(methods=["GET"])
def suggestions():
    guard("enable_assistant")
    return ["How many annual leave days do I have left?", "What is the reimbursement policy for travel?",
            "When is the next public holiday?", "Where can I find my latest payslip?",
            "Apply for leave next Sunday", "How do I request a salary certificate?"]
