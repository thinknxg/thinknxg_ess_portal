# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import getdate


class ESSCheckinPolicy(Document):
    def validate(self):
        if self.valid_from and self.valid_until and getdate(self.valid_until) < getdate(self.valid_from):
            frappe.throw(_("Valid until must be on or after valid from."))
        for f in ("radius_override", "accuracy_override"):
            if self.get(f) and not 5 <= self.get(f) <= 5000:
                frappe.throw(_("{0} must be between 5 and 5,000 m.").format(self.meta.get_label(f)))
        if self.location_mode == "Only these locations" and not self.locations:
            frappe.throw(_("Add at least one location, or choose 'Add to default locations'."))

    def on_update(self):
        from thinknxg_ess_portal.services.audit import log_event
        log_event("Settings Change", self.doctype, self.name, employee=self.employee,
                  details=f"access={self.checkin_access} gps={self.gps_requirement} window={self.shift_window} "
                          f"active={self.is_active} reason={self.reason[:200]}")
