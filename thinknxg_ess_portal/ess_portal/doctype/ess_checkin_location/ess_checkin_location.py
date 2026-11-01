# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

class ESSCheckinLocation(Document):
    def validate(self):
        if self.shift_location and (not self.latitude or not self.longitude):
            loc = frappe.db.get_value("Shift Location", self.shift_location,
                                      ["latitude", "longitude", "checkin_radius"], as_dict=True)
            if loc:
                self.latitude, self.longitude = loc.latitude, loc.longitude
                self.radius = self.radius or loc.checkin_radius
        if not (-90 <= (self.latitude or 0) <= 90 and -180 <= (self.longitude or 0) <= 180) or (
                not self.latitude and not self.longitude):
            frappe.throw(_("Enter valid latitude and longitude."))
        if not 10 <= (self.radius or 0) <= 5000:
            frappe.throw(_("Radius must be between 10 m and 5,000 m."))

    def on_update(self):
        frappe.cache.delete_value("ess_checkin_locations")
        from thinknxg_ess_portal.services.audit import log_event
        log_event("Settings Change", self.doctype, self.name,
                  details=f"location {self.latitude},{self.longitude} r={self.radius} active={self.is_active}")

    def on_trash(self):
        frappe.cache.delete_value("ess_checkin_locations")
