# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import get_datetime


class ESSAnnouncement(Document):
    def validate(self):
        if self.publish_from and self.publish_until and get_datetime(self.publish_until) <= get_datetime(self.publish_from):
            frappe.throw(_("Publish until must be after publish from"))
