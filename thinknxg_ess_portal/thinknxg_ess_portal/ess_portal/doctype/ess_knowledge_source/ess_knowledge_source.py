# Copyright (c) 2026, Kreatao and contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document

class ESSKnowledgeSource(Document):
    def on_update(self):
        frappe.enqueue("thinknxg_ess_portal.services.ai_retrieval.index_source", source=self.name,
                       queue="short", enqueue_after_commit=True, job_id=f"ess_index::{self.name}",
                       deduplicate=True)

    def on_trash(self):
        frappe.db.delete("ESS Knowledge Chunk", {"source": self.name})
