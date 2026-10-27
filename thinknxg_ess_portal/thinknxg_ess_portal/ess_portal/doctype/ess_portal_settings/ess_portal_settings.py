# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

class ESSPortalSettings(Document):
    def validate(self):
        if (self.min_group_size or 0) < 3:
            frappe.throw(_("Minimum group size must be at least 3 to protect individuals."))
        if self.ai_provider == "OpenAI Compatible" and not self.ai_base_url:
            frappe.throw(_("Base URL is required for OpenAI-compatible providers."))

    def on_update(self):
        frappe.cache.delete_value("ess_portal_settings")
        from thinknxg_ess_portal.services.audit import log_event
        log_event("Settings Change", reference_doctype=self.doctype, reference_name=self.name,
                  details="Portal settings updated")
