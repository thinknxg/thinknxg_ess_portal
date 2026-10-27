# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

class ESSPolicyAcknowledgement(Document):
    def before_insert(self):
        if frappe.db.exists("ESS Policy Acknowledgement", {"employee": self.employee, "policy": self.policy}):
            frappe.throw(_("Policy already acknowledged"), frappe.DuplicateEntryError)
        self.policy_version = frappe.db.get_value("ESS Policy", self.policy, "version")
