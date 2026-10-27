# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import getdate


class ESSEmployeeDocument(Document):
    def validate(self):
        if self.issue_date and self.expiry_date and getdate(self.expiry_date) < getdate(self.issue_date):
            frappe.throw(_("Expiry date cannot be before issue date"))
        if self.verified and not self.verified_by:
            self.verified_by = frappe.session.user
