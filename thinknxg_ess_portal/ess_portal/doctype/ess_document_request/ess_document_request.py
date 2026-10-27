# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

class ESSDocumentRequest(Document):
    def before_insert(self):
        self.template_version = frappe.db.get_value("ESS Document Template", self.template, "version")

    def on_trash(self):
        if self.status == "Generated" and not frappe.has_permission("ESS Document Request", "delete"):
            frappe.throw(_("Generated documents cannot be deleted"))
