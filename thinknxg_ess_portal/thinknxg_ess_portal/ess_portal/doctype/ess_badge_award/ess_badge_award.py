# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

from frappe.utils import today


class ESSBadgeAward(Document):
    def before_insert(self):
        self.awarded_on = self.awarded_on or today()
        self.awarded_by = self.awarded_by or frappe.session.user
        if frappe.db.exists("ESS Badge Award", {"employee": self.employee, "badge": self.badge}):
            frappe.throw(_("Badge already awarded"), frappe.DuplicateEntryError)

    def after_insert(self):
        user = frappe.db.get_value("Employee", self.employee, "user_id")
        if user:
            from thinknxg_ess_portal.services.notifications import notify
            notify(user, "Recognition", _("You earned the {0} badge").format(self.badge),
                   self.reason or "", "/ess/recognition", self.doctype, self.name)
