# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import now_datetime


class ESSHRTicketComment(Document):
    def before_insert(self):
        self.author = self.author or frappe.session.user
        self.author_name = frappe.utils.get_fullname(self.author)

    def after_insert(self):
        ticket = frappe.get_doc("ESS HR Ticket", self.ticket)
        if self.via == "Agent" and not self.is_internal and not ticket.first_responded_on:
            ticket.db_set("first_responded_on", now_datetime())
        frappe.publish_realtime("ess_ticket_update", {"ticket": self.ticket}, doctype="ESS HR Ticket",
                                docname=self.ticket, after_commit=True)
