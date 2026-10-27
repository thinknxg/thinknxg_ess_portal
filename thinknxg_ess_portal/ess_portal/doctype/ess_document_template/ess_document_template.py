# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

class ESSDocumentTemplate(Document):
    def validate(self):
        self.template_key = frappe.scrub(self.template_key or self.template_name)
        before = self.get_doc_before_save()
        if before and before.template_html != self.template_html:
            self.version = (self.version or 1) + 1
        from frappe.utils.jinja import validate_template
        validate_template(self.template_html)
        if self.include_salary and not self.requires_approval:
            frappe.msgprint(_("Salary templates should normally require approval."), indicator="orange")
