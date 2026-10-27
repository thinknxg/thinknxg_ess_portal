import frappe
from frappe import _
from frappe.utils import now_datetime, cint
from thinknxg_ess_portal.api._guard import guard
from thinknxg_ess_portal.services import identity


def audience_condition(emp, alias="a"):
    return (f"({alias}.audience='All Employees' or ({alias}.audience='Company' and {alias}.company=%(company)s) or "
            f"({alias}.audience='Department' and {alias}.department=%(department)s) or "
            f"({alias}.audience='Branch' and {alias}.branch=%(branch)s) or "
            f"({alias}.audience='Designation' and {alias}.designation=%(designation)s))")


def _visible_announcements(emp, limit=20):
    vals = {"company": emp.company, "department": emp.department or "", "branch": emp.get("branch") or "",
            "designation": emp.designation or "", "now": now_datetime(), "user": frappe.session.user}
    return frappe.db.sql(f"""select a.name, a.title, a.category, a.body, a.image, a.is_pinned, a.publish_from,
            exists(select 1 from `tabESS Announcement Read` r where r.announcement=a.name and r.user=%(user)s) is_read
        from `tabESS Announcement` a where a.is_published=1 and {audience_condition(emp)}
          and (a.publish_from is null or a.publish_from<=%(now)s) and (a.publish_until is null or a.publish_until>=%(now)s)
        order by a.is_pinned desc, coalesce(a.publish_from, a.creation) desc limit {int(limit)}""", vals, as_dict=True)


@frappe.whitelist(methods=["GET"])
def list_announcements(limit=30):
    emp = guard()
    return _visible_announcements(emp, min(cint(limit) or 30, 100))


@frappe.whitelist(methods=["POST"])
def mark_read(name):
    emp = guard()
    if not any(a.name == name for a in _visible_announcements(emp, 500)):
        frappe.throw(_("Not found"), frappe.DoesNotExistError)
    if not frappe.db.exists("ESS Announcement Read", {"announcement": name, "user": frappe.session.user}):
        frappe.get_doc({"doctype": "ESS Announcement Read", "announcement": name, "user": frappe.session.user,
                        "read_on": now_datetime()}).insert(ignore_permissions=True)
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def save_announcement(title, body, category="General", audience="All Employees", company=None, department=None,
                      branch=None, designation=None, publish_from=None, publish_until=None, is_pinned=0,
                      is_published=0, name=None):
    guard(employee=False)
    if not identity.is_hr():
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    doc = frappe.get_doc("ESS Announcement", name) if name else frappe.new_doc("ESS Announcement")
    doc.update({"title": title, "body": frappe.utils.sanitize_html(body), "category": category, "audience": audience,
                "company": company, "department": department, "branch": branch, "designation": designation,
                "publish_from": publish_from or None, "publish_until": publish_until or None,
                "is_pinned": cint(is_pinned), "is_published": cint(is_published)})
    doc.save(ignore_permissions=True)
    return {"name": doc.name}


@frappe.whitelist(methods=["GET"])
def admin_list():
    guard(employee=False)
    if not identity.is_hr():
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    rows = frappe.get_all("ESS Announcement", fields=["name", "title", "category", "audience", "is_published",
                                                      "is_pinned", "publish_from", "publish_until", "modified"],
                          order_by="modified desc", limit=100)
    for r in rows:
        r["reads"] = frappe.db.count("ESS Announcement Read", {"announcement": r.name})
    return rows
