# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import getdate


class ESSRosterChangeRequest(Document):
    def validate(self):
        if getdate(self.to_date) < getdate(self.from_date):
            frappe.throw(_("To date must be on or after from date."))
        if self.request_type == "Swap with colleague":
            if not self.swap_with or self.swap_with == self.employee:
                frappe.throw(_("Choose the colleague to swap with."))
        elif self.request_type == "Change shift" and not self.requested_shift_type:
            frappe.throw(_("Choose the shift you'd like."))
