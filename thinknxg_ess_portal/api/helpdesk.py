import frappe
from frappe import _
from frappe.utils import cint, now_datetime, date_diff, today, add_days
from thinknxg_ess_portal.api._guard import guard, parse, page
from thinknxg_ess_portal.services import identity
from thinknxg_ess_portal.services.idempotency import run_once
from thinknxg_ess_portal.services.ratelimit import check_rate
from thinknxg_ess_portal.permissions import ticket_has_permission
from thinknxg_ess_portal.ess_portal.doctype.ess_hr_ticket.ess_hr_ticket import TRANSITIONS

TICKET_FIELDS = ["name", "subject", "category", "priority", "status", "assigned_to", "employee", "employee_name",
                 "department", "sla_status", "first_response_due", "resolution_due", "first_responded_on",
                 "resolved_on", "rating", "creation", "modified", "is_confidential", "escalation_level", "channel"]


def _ticket(name, ptype="read"):
    doc = frappe.get_doc("ESS HR Ticket", name)
    if not ticket_has_permission(doc, ptype):
        frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)
    return doc


def _is_staff_on(doc):
    return ticket_has_permission(doc, "write") and identity.is_agent()


@frappe.whitelist(methods=["GET"])
def categories():
    guard("enable_helpdesk", employee=False)
    return frappe.get_all("ESS HR Ticket Category", filters={"visible_to_employees": 1},
                          fields=["name", "icon", "description", "first_response_hours", "resolution_hours"],
                          order_by="name")


@frappe.whitelist(methods=["GET"])
def my_tickets(status=None, limit=30, offset=0):
    emp = guard("enable_helpdesk")
    limit, offset = page(limit, offset)
    flt = {"employee": emp.name}
    if status == "open":
        flt["status"] = ["not in", ["Resolved", "Closed"]]
    elif status == "closed":
        flt["status"] = ["in", ["Resolved", "Closed"]]
    return frappe.get_all("ESS HR Ticket", filters=flt, fields=TICKET_FIELDS, order_by="modified desc",
                          limit=limit, start=offset)


@frappe.whitelist(methods=["POST"])
def create_ticket(category, subject, description, priority="Medium", attachments=None, channel="Portal",
                  client_request_id=None):
    emp = guard("enable_helpdesk")
    check_rate("ticket", identity.settings().get("ticket_rate_limit_per_hour") or 10)
    if not frappe.db.get_value("ESS HR Ticket Category", category, "visible_to_employees"):
        frappe.throw(_("Invalid category"))
    if priority not in ("Low", "Medium", "High", "Urgent"):
        priority = "Medium"
    if not (subject or "").strip():
        frappe.throw(_("Subject is required"))

    def do():
        doc = frappe.get_doc({"doctype": "ESS HR Ticket", "employee": emp.name, "category": category,
                              "subject": subject.strip()[:140], "description": frappe.utils.sanitize_html(description or ""),
                              "priority": priority, "channel": channel if channel in ("Portal", "Assistant") else "Portal",
                              "raised_by": frappe.session.user, "client_request_id": client_request_id})
        doc.insert(ignore_permissions=True)
        _attach(parse(attachments, []), doc.name)
        return {"doctype": doc.doctype, "name": doc.name, "status": doc.status}

    return run_once(client_request_id, "hr_ticket", do)


def _attach(files, ticket):
    for url in files[:10]:
        f = frappe.db.get_value("File", {"file_url": url, "owner": frappe.session.user}, "name")
        if f:
            frappe.db.set_value("File", f, {"attached_to_doctype": "ESS HR Ticket", "attached_to_name": ticket,
                                            "is_private": 1})


@frappe.whitelist(methods=["GET"])
def get_ticket(name):
    guard("enable_helpdesk", employee=False)
    doc = _ticket(name)
    staff = _is_staff_on(doc)
    flt = {"ticket": name}
    if not staff:
        flt["is_internal"] = 0
    comments = frappe.get_all("ESS HR Ticket Comment", filters=flt,
                              fields=["name", "author", "author_name", "via", "is_internal", "comment", "creation"],
                              order_by="creation asc")
    files = frappe.get_all("File", filters={"attached_to_doctype": "ESS HR Ticket", "attached_to_name": name},
                           fields=["file_name", "file_url", "owner", "creation"])
    out = {f: doc.get(f) for f in TICKET_FIELDS}
    out.update({"description": doc.description, "rating_comment": doc.rating_comment, "reopen_count": doc.reopen_count,
                "comments": comments, "attachments": files, "is_staff": staff,
                "assigned_to_name": frappe.utils.get_fullname(doc.assigned_to) if doc.assigned_to else None,
                "can_reopen": doc.status in ("Resolved", "Closed") and doc.resolved_on and date_diff(
                    today(), doc.resolved_on) <= cint(identity.settings().get("allow_reopen_days") or 7),
                "transitions": sorted(TRANSITIONS.get(doc.status, [])) if staff else []})
    return out


@frappe.whitelist(methods=["POST"])
def reply(name, comment, internal=0, attachments=None, client_request_id=None):
    guard("enable_helpdesk", employee=False)
    doc = _ticket(name)
    staff = _is_staff_on(doc)
    if cint(internal) and not staff:
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    if doc.status == "Closed" and not staff:
        frappe.throw(_("This ticket is closed. Reopen it to continue."))
    if not frappe.utils.strip_html(comment or "").strip():
        frappe.throw(_("Message is empty"))

    def do():
        c = frappe.get_doc({"doctype": "ESS HR Ticket Comment", "ticket": name, "comment": frappe.utils.sanitize_html(comment),
                            "is_internal": cint(internal), "via": "Agent" if staff else "Employee"})
        c.insert(ignore_permissions=True)
        _attach(parse(attachments, []), name)
        if not staff and doc.status == "Waiting for Employee":
            frappe.flags.ess_force_transition = True
            doc.status = "In Progress"
            doc.save(ignore_permissions=True)
        elif staff and not cint(internal) and doc.status in ("Open", "Assigned"):
            doc.status = "In Progress"
            doc.save(ignore_permissions=True)
        if not cint(internal):
            from thinknxg_ess_portal.services.notifications import notify
            target = doc.raised_by if staff else doc.assigned_to
            notify(target, "Helpdesk", _("New reply on {0}").format(doc.name), frappe.utils.strip_html(comment)[:140],
                   f"/ess/support/{name}" if staff else f"/ess/hr/tickets/{name}", doc.doctype, name)
        return {"doctype": c.doctype, "name": c.name}

    return run_once(client_request_id, "ticket_reply", do)


@frappe.whitelist(methods=["POST"])
def reopen(name, reason):
    emp = guard("enable_helpdesk")
    doc = _ticket(name)
    if doc.employee != emp.name:
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    days = cint(identity.settings().get("allow_reopen_days") or 7)
    if doc.status not in ("Resolved", "Closed") or (doc.resolved_on and date_diff(today(), doc.resolved_on) > days):
        frappe.throw(_("This ticket can no longer be reopened. Please raise a new one."))
    frappe.get_doc({"doctype": "ESS HR Ticket Comment", "ticket": name, "via": "Employee",
                    "comment": _("Reopened: {0}").format(frappe.utils.escape_html(reason or ""))}).insert(ignore_permissions=True)
    doc.status = "In Progress"
    doc.save(ignore_permissions=True)
    return {"name": name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def rate(name, rating, comment=None):
    emp = guard("enable_helpdesk")
    doc = _ticket(name)
    if doc.employee != emp.name or doc.status not in ("Resolved", "Closed"):
        frappe.throw(_("You can rate resolved tickets only"))
    r = max(1, min(cint(rating), 5))
    doc.db_set({"rating": r / 5.0, "rating_comment": (comment or "")[:500]})
    return {"name": name, "rating": r}


@frappe.whitelist(methods=["POST"])
def close(name):
    emp = guard("enable_helpdesk")
    doc = _ticket(name)
    if doc.employee != emp.name:
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    frappe.flags.ess_force_transition = True
    doc.status = "Closed"
    doc.save(ignore_permissions=True)
    return {"name": name, "status": "Closed"}


# ------------------------------------------------------------------ HR service desk
def _agent():
    guard("enable_helpdesk", employee=False)
    if not identity.is_agent():
        frappe.throw(_("Service desk access is for HR agents."), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def queue(status=None, category=None, priority=None, assigned=None, q=None, sla=None, limit=50, offset=0):
    _agent()
    from thinknxg_ess_portal.permissions import ticket_query
    limit, offset = page(limit, offset)
    cond = [ticket_query(frappe.session.user) or "1=1"]
    vals = {}
    if status == "open":
        cond.append("status not in ('Resolved','Closed')")
    elif status:
        cond.append("status=%(status)s"); vals["status"] = status
    if category:
        cond.append("category=%(category)s"); vals["category"] = category
    if priority:
        cond.append("priority=%(priority)s"); vals["priority"] = priority
    if sla:
        cond.append("sla_status=%(sla)s"); vals["sla"] = sla
    if assigned == "me":
        cond.append("assigned_to=%(me)s"); vals["me"] = frappe.session.user
    elif assigned == "unassigned":
        cond.append("ifnull(assigned_to,'')=''")
    if q:
        cond.append("(subject like %(q)s or name like %(q)s or employee_name like %(q)s)"); vals["q"] = f"%{q[:60]}%"
    where = " and ".join(cond)
    rows = frappe.db.sql(f"""select {", ".join(TICKET_FIELDS)} from `tabESS HR Ticket` where {where}
        order by field(priority,'Urgent','High','Medium','Low'), resolution_due asc limit {limit} offset {offset}""",
                         vals, as_dict=True)
    stats = frappe.db.sql(f"""select status, sla_status, count(*) n from `tabESS HR Ticket` where {cond[0]}
        and status not in ('Closed') group by status, sla_status""", as_dict=True)
    return {"tickets": rows, "stats": stats}


@frappe.whitelist(methods=["POST"])
def assign(name, user):
    _agent()
    doc = _ticket(name, "write")
    if not frappe.db.exists("User", {"name": user, "enabled": 1}):
        frappe.throw(_("Invalid user"))
    doc.assigned_to = user
    if doc.status == "Open":
        doc.status = "Assigned"
    doc.save(ignore_permissions=True)
    return {"name": name, "assigned_to": user}


@frappe.whitelist(methods=["POST"])
def set_status(name, status, note=None):
    _agent()
    doc = _ticket(name, "write")
    doc.status = status
    doc.save(ignore_permissions=True)
    if note:
        frappe.get_doc({"doctype": "ESS HR Ticket Comment", "ticket": name, "via": "Agent", "is_internal": 0,
                        "comment": frappe.utils.sanitize_html(note)}).insert(ignore_permissions=True)
    return {"name": name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def set_priority(name, priority):
    _agent()
    doc = _ticket(name, "write")
    if priority not in ("Low", "Medium", "High", "Urgent"):
        frappe.throw(_("Invalid priority"))
    doc.priority = priority
    doc.save(ignore_permissions=True)
    return {"name": name, "priority": priority}


@frappe.whitelist(methods=["GET"])
def agents():
    _agent()
    users = frappe.get_all("Has Role", filters={"role": ["in", ["ESS HR Agent", "ESS Payroll Officer", "HR Manager"]],
                                                "parenttype": "User"}, pluck="parent", distinct=True)
    return [{"user": u, "name": frappe.utils.get_fullname(u)} for u in users if u not in ("Administrator", "Guest")]


@frappe.whitelist(methods=["GET"])
def canned_responses(category=None):
    _agent()
    flt = {"category": ["in", [category, "", None]]} if category else {}
    return frappe.get_all("ESS Canned Response", filters=flt, fields=["name", "title", "response", "category"])


@frappe.whitelist(methods=["GET"])
def faqs(q=None):
    guard("enable_helpdesk", employee=False)
    if q:
        from thinknxg_ess_portal.services.ai_retrieval import search
        return [{"title": h["title"], "section": h["heading"], "snippet": h["snippet"]}
                for h in search(q, k=5, source_type="FAQ")]
    return frappe.get_all("ESS Knowledge Source", filters={"source_type": "FAQ", "is_active": 1,
                                                           "audience": "All Employees"},
                          fields=["name", "title", "content"], limit=30)
