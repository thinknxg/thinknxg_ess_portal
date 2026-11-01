# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import getdate, date_diff


class ESSRoster(Document):
    def validate(self):
        if getdate(self.to_date) < getdate(self.from_date):
            frappe.throw(_("To date must be on or after from date."))
        if date_diff(self.to_date, self.from_date) > 62:
            frappe.throw(_("A roster can cover at most 63 days."))
        self.planner = self.planner or frappe.session.user

    def on_trash(self):
        if self.status == "Published":
            frappe.throw(_("Archive a published roster instead of deleting it."))
        frappe.db.delete("ESS Roster Entry", {"roster": self.name})
