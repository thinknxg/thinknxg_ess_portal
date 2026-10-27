# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import getdate


class ESSApprovalDelegation(Document):
    def validate(self):
        if self.delegator == self.delegate:
            frappe.throw(_("You cannot delegate to yourself"))
        if getdate(self.to_date) < getdate(self.from_date):
            frappe.throw(_("To date must be on or after from date"))
        overlap = frappe.db.sql(
            """select name from `tabESS Approval Delegation` where delegator=%s and is_active=1 and name!=%s
               and from_date<=%s and to_date>=%s""",
            (self.delegator, self.name or "", self.to_date, self.from_date))
        if overlap and self.is_active:
            frappe.throw(_("An active delegation already covers part of this period ({0})").format(overlap[0][0]))

    def on_update(self):
        from thinknxg_ess_portal.services.audit import log_event
        log_event("Delegation", reference_doctype=self.doctype, reference_name=self.name,
                  details=f"{self.delegator} -> {self.delegate} {self.from_date}..{self.to_date} active={self.is_active}")
