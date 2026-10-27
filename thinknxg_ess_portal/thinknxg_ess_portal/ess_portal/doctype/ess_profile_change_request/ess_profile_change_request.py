# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

BANK_FIELDS = {"bank_name", "bank_ac_no", "iban"}


class ESSProfileChangeRequest(Document):
    def validate(self):
        from thinknxg_ess_portal.services.profile import editable_fields
        allowed = editable_fields()
        for row in self.items:
            if row.field_name not in allowed:
                frappe.throw(_("Field {0} cannot be changed through the portal").format(row.field_name))
        self.contains_bank_details = int(any(r.field_name in BANK_FIELDS for r in self.items))
