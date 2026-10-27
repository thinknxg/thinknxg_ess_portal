# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

class ESSRecognitionReaction(Document):
    def validate(self):
        if frappe.db.exists("ESS Recognition Reaction", {"recognition": self.recognition, "user": self.user,
                                                         "reaction": self.reaction, "name": ["!=", self.name]}):
            frappe.throw(_("Already reacted"), frappe.DuplicateEntryError)

    def after_insert(self):
        self._recount()

    def on_trash(self):
        self._recount(-1)

    def _recount(self, delta=0):
        count = frappe.db.count("ESS Recognition Reaction", {"recognition": self.recognition}) + delta
        frappe.db.set_value("ESS Recognition", self.recognition, "reaction_count", max(count, 0),
                            update_modified=False)
