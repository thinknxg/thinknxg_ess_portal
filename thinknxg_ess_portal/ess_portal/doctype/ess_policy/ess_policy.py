# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

class ESSPolicy(Document):
    def autoname(self):
        self.name = f"{frappe.scrub(self.policy_code).upper()}-v{self.version}"
