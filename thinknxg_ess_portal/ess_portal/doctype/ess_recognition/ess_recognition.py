# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import now_datetime


class ESSRecognition(Document):
    def before_insert(self):
        self.sender = self.sender or frappe.session.user
        self.sender_name = frappe.utils.get_fullname(self.sender)
        self.posted_on = now_datetime()

    def validate(self):
        if self.recipient_user and self.recipient_user == self.sender:
            frappe.throw(_("You cannot recognise yourself"))
        if (self.points or 0) < 0:
            frappe.throw(_("Points cannot be negative"))

    def on_update(self):
        before = self.get_doc_before_save()
        became_visible = self.status == "Approved" and (not before or before.status != "Approved")
        if became_visible and self.recipient_user:
            from thinknxg_ess_portal.services.notifications import notify
            notify(self.recipient_user, "Recognition", _("{0} recognised you").format(self.sender_name),
                   self.message[:140], "/ess/recognition", self.doctype, self.name)
