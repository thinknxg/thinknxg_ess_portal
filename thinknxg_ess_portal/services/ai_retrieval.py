"""Lightweight, dependency-free retrieval over approved HR knowledge sources (BM25).

Permission filtering happens BEFORE scoring: a chunk the user cannot see is never a candidate.
"""
import math
import re
from collections import Counter

import frappe
from frappe.utils import now_datetime, strip_html
from thinknxg_ess_portal.services import identity

STOP = set("""a an the and or of to in on for with is are was were be been by at as it this that these those
from your you my our we i me can do does how what when where which who why will would should could
policy policies please tell about any""".split())
WORD = re.compile(r"[\w؀-ۿ]+", re.UNICODE)


def terms(text):
    return [t for t in (w.lower() for w in WORD.findall(text or "")) if len(t) > 1 and t not in STOP]


def _extract_attachment(file_url):
    if not file_url:
        return ""
    try:
        f = frappe.get_doc("File", {"file_url": file_url})
        content = f.get_content()
        if file_url.lower().endswith(".pdf"):
            try:
                import io
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(content))
                return "\n".join((p.extract_text() or "") for p in reader.pages)
            except ImportError:
                return ""
        return content.decode("utf-8", "ignore") if isinstance(content, bytes) else str(content)
    except Exception:
        frappe.log_error(title="ESS knowledge attachment extraction failed")
        return ""


def _chunks(text, size=900):
    blocks, heading, buf = [], None, ""
    for para in re.split(r"\n\s*\n|(?<=</p>)|(?<=</li>)", text):
        p = strip_html(para or "").strip()
        if not p:
            continue
        if len(p) < 80 and not p.endswith(".") and len(buf) > 0:
            blocks.append((heading, buf.strip()))
            heading, buf = p, ""
            continue
        if len(p) < 80 and not p.endswith(".") and not buf:
            heading = p
            continue
        if len(buf) + len(p) > size and buf:
            blocks.append((heading, buf.strip()))
            buf = ""
        buf += p + "\n"
    if buf.strip():
        blocks.append((heading, buf.strip()))
    return blocks


def index_source(source):
    s = frappe.get_doc("ESS Knowledge Source", source)
    frappe.db.delete("ESS Knowledge Chunk", {"source": source})
    if s.is_active:
        text = (s.content or "") + "\n\n" + _extract_attachment(s.attachment)
        for i, (heading, body) in enumerate(_chunks(text)):
            frappe.get_doc({"doctype": "ESS Knowledge Chunk", "source": source, "chunk_index": i,
                            "heading": (heading or s.title)[:140], "content": body,
                            "terms": " ".join(terms(f"{s.title} {heading or ''} {body}")),
                            "audience": s.audience, "company": s.company or "", "department": s.department or ""
                            }).insert(ignore_permissions=True)
    count = frappe.db.count("ESS Knowledge Chunk", {"source": source})
    s.db_set({"last_indexed_on": now_datetime(), "chunk_count": count}, update_modified=False)
    frappe.cache.delete_value("ess_kb_corpus")
    frappe.db.commit()


def _corpus():
    data = frappe.cache.get_value("ess_kb_corpus")
    if data is None:
        rows = frappe.db.sql("""select c.name, c.source, c.heading, c.content, c.terms, c.audience, c.company,
                c.department, s.title, s.source_type from `tabESS Knowledge Chunk` c
                join `tabESS Knowledge Source` s on s.name=c.source where s.is_active=1""", as_dict=True)
        data = [dict(r) for r in rows]
        frappe.cache.set_value("ess_kb_corpus", data, expires_in_sec=600)
    return data


def _visible(chunk, user, emp):
    aud = chunk["audience"]
    if aud == "HR Only" and not identity.is_hr(user):
        return False
    if aud == "Managers" and not (identity.is_manager(user) or identity.is_hr(user)):
        return False
    if chunk["company"] and (not emp or chunk["company"] != emp.company):
        return identity.is_hr_manager(user)
    if chunk["department"] and (not emp or chunk["department"] != emp.department):
        return identity.is_hr(user)
    return True


def search(query, k=5, user=None, source_type=None):
    user = user or frappe.session.user
    emp = identity.get_employee(user, required=False)
    q = terms(query)
    if not q:
        return []
    docs = [c for c in _corpus() if _visible(c, user, emp) and (not source_type or c["source_type"] == source_type)]
    if not docs:
        return []
    N = len(docs)
    tokenised = [c["terms"].split() for c in docs]
    avgdl = sum(len(t) for t in tokenised) / N or 1
    df = Counter()
    for t in tokenised:
        df.update(set(t))
    k1, b = 1.4, 0.75
    scored = []
    for c, toks in zip(docs, tokenised):
        tf = Counter(toks)
        score = 0.0
        for term in q:
            if term not in tf:
                continue
            idf = math.log(1 + (N - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(toks) / avgdl))
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [{"chunk": c["name"], "source": c["source"], "title": c["title"], "heading": c["heading"],
             "content": c["content"][:1500], "snippet": c["content"][:260], "score": round(s, 3),
             "source_type": c["source_type"]} for s, c in scored[:k]]
