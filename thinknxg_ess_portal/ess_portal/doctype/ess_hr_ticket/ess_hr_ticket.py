# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import now_datetime, add_to_date, get_datetime

TRANSITIONS = {
    "Open": {"Assigned", "In Progress", "Resolved", "Closed"},
    "Assigned": {"In Progress", "Waiting for Employee", "Resolved", "Open"},
    "In Progress": {"Waiting for Employee", "Resolved", "Assigned"},
    "Waiting for Employee": {"In Progress", "Resolved", "Closed"},
    "Resolved": {"Closed", "In Progress"},
    "Closed": {"In Progress"},
}


class ESSHRTicket(Document):
    def before_insert(self):
        self.raised_by = self.raised_by or frappe.session.user
        cat = frappe.get_cached_doc("ESS HR Ticket Category", self.category)
        now = now_datetime()
        self.first_response_due = add_to_date(now, hours=cat.first_response_hours or 4)
        self.resolution_due = add_to_date(now, hours=cat.resolution_hours or 24)
        if not self.assigned_to:
            self.assigned_to = cat.default_assignee or frappe.db.get_single_value(
                "ESS Portal Settings", "default_ticket_assignee")
        if self.assigned_to and self.status == "Open":
            self.status = "Assigned"

    def validate(self):
        before = self.get_doc_before_save()
        if before and before.status != self.status:
            allowed = TRANSITIONS.get(before.status, set())
            if self.status not in allowed and not frappe.flags.ess_force_transition:
                frappe.throw(_("Cannot move ticket from {0} to {1}").format(before.status, self.status))
            if self.status == "Resolved":
                self.resolved_on = now_datetime()
            if self.status == "Closed":
                self.closed_on = now_datetime()
            if before.status in ("Resolved", "Closed") and self.status == "In Progress":
                self.reopen_count = (self.reopen_count or 0) + 1
                self.resolved_on = None
                self.closed_on = None
        self.update_sla_status()

    def update_sla_status(self):
        if self.status in ("Resolved", "Closed"):
            return
        now = now_datetime()
        due = get_datetime(self.resolution_due) if self.resolution_due else None
        if due and now > due:
            self.sla_status = "Breached"
        elif due and (due - now).total_seconds() < 0.25 * 3600 * max(
                frappe.db.get_value("ESS HR Ticket Category", self.category, "resolution_hours") or 24, 1):
            self.sla_status = "At Risk"
        else:
            self.sla_status = "On Track"

    def on_update(self):
        before = self.get_doc_before_save()
        if before and before.assigned_to != self.assigned_to and self.assigned_to:
            from thinknxg_ess_portal.services.notifications import notify
            notify(self.assigned_to, "Helpdesk", _("Ticket {0} assigned to you").format(self.name),
                   self.subject, f"/ess/hr/tickets/{self.name}", self.doctype, self.name)
        if before and before.status != self.status and self.raised_by:
            from thinknxg_ess_portal.services.notifications import notify
            notify(self.raised_by, "Helpdesk", _("Ticket {0} is now {1}").format(self.name, _(self.status)),
                   self.subject, f"/ess/support/{self.name}", self.doctype, self.name)
