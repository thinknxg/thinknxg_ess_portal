# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

class ESSShiftPattern(Document):
    def validate(self):
        for row in self.steps:
            if not row.is_rest_day and not row.shift_type:
                frappe.throw(_("Row {0}: choose a shift or mark it as a rest day.").format(row.idx))
            if row.is_rest_day:
                row.shift_type = None
