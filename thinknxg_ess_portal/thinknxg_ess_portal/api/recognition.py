import frappe
from frappe import _
from frappe.utils import cint, get_first_day, today
from thinknxg_ess_portal.api._guard import guard, page
from thinknxg_ess_portal.services import identity
from thinknxg_ess_portal.services.idempotency import run_once

REACTIONS = ("clap", "celebrate", "heart", "highfive", "insight")


def _budget_used(user):
    return cint(frappe.db.sql("""select sum(points) from `tabESS Recognition` where sender=%s
        and status!='Rejected' and creation>=%s""", (user, get_first_day(today())))[0][0])


@frappe.whitelist(methods=["GET"])
def feed(scope="all", limit=20, offset=0):
    emp = guard("enable_recognition")
    limit, offset = page(limit, offset)
    user = frappe.session.user
    if scope == "mine":
        flt = [["status", "=", "Approved"]]
        rows = frappe.get_all("ESS Recognition", filters=flt, or_filters={"recipient": emp.name, "sender": user},
                              fields=["*"], order_by="posted_on desc", limit=limit, start=offset)
    elif scope == "team" and identity.is_manager():
        team = identity.team_employees() + [emp.name]
        rows = frappe.get_all("ESS Recognition", filters={"status": "Approved", "recipient": ["in", team],
                                                          "visibility": ["in", ["Public", "Team"]]},
                              fields=["*"], order_by="posted_on desc", limit=limit, start=offset)
    else:
        rows = frappe.get_all("ESS Recognition", filters={"status": "Approved", "visibility": "Public"},
                              fields=["*"], order_by="posted_on desc", limit=limit, start=offset)
    names = [r.name for r in rows] or [""]
    reacts = frappe.get_all("ESS Recognition Reaction", filters={"recognition": ["in", names]},
                            fields=["recognition", "reaction", "user"])
    cats = {c.name: c.icon for c in frappe.get_all("ESS Recognition Category", fields=["name", "icon"])}
    out = []
    for r in rows:
        mine = [x.reaction for x in reacts if x.recognition == r.name and x.user == user]
        tally = {}
        for x in reacts:
            if x.recognition == r.name:
                tally[x.reaction] = tally.get(x.reaction, 0) + 1
        out.append({"name": r.name, "sender_name": r.sender_name, "recipient": r.recipient,
                    "recipient_name": r.recipient_name, "category": r.category, "icon": cats.get(r.category, "🌟"),
                    "message": r.message, "points": r.points, "posted_on": r.posted_on, "visibility": r.visibility,
                    "reactions": tally, "my_reactions": mine})
    return out


@frappe.whitelist(methods=["GET"])
def summary():
    emp = guard("enable_recognition")
    user = frappe.session.user
    budget = cint(identity.settings().get("monthly_points_budget"))
    badges = frappe.db.sql("""select a.badge, a.awarded_on, b.icon, b.color, b.description from `tabESS Badge Award` a
        join `tabESS Badge` b on b.name=a.badge where a.employee=%s order by a.awarded_on desc""", emp.name, as_dict=True)
    catalog = frappe.get_all("ESS Badge", filters={"is_active": 1},
                             fields=["name", "icon", "color", "description", "rule_type", "threshold"])
    return {
        "received": frappe.db.count("ESS Recognition", {"recipient": emp.name, "status": "Approved"}),
        "given": frappe.db.count("ESS Recognition", {"sender": user, "status": "Approved"}),
        "points_received": cint(frappe.db.sql("""select sum(points) from `tabESS Recognition` where recipient=%s
                                 and status='Approved'""", emp.name)[0][0]),
        "budget": budget, "budget_remaining": max(budget - _budget_used(user), 0),
        "badges": badges, "catalog": catalog,
        "categories": frappe.get_all("ESS Recognition Category", filters={"is_active": 1},
                                     fields=["name", "icon", "value_statement", "default_points"]),
        "by_category": frappe.db.sql("""select category, count(*) n from `tabESS Recognition` where recipient=%s
                         and status='Approved' group by category""", emp.name, as_dict=True),
    }


@frappe.whitelist(methods=["POST"])
def give(recipient, message, category=None, visibility="Public", points=None, client_request_id=None):
    emp = guard("enable_recognition")
    s = identity.settings()
    if recipient == emp.name:
        frappe.throw(_("You cannot recognise yourself"))
    rec = frappe.db.get_value("Employee", recipient, ["status", "company"], as_dict=True)
    if not rec or rec.status != "Active" or rec.company != emp.company:
        frappe.throw(_("Choose an active colleague"))
    if visibility not in ("Public", "Team", "Private") or (visibility == "Public" and not s.allow_public_recognition):
        visibility = "Team"
    if len((message or "").strip()) < 10:
        frappe.throw(_("Please write a meaningful message (10+ characters)."))
    cat_points = cint(frappe.db.get_value("ESS Recognition Category", category, "default_points")) if category else 0
    pts = max(0, min(cint(points) if points not in (None, "") else cat_points, 50))
    budget = cint(s.monthly_points_budget)
    if budget and _budget_used(frappe.session.user) + pts > budget:
        frappe.throw(_("This exceeds your monthly recognition points budget."))

    def do():
        doc = frappe.get_doc({"doctype": "ESS Recognition", "recipient": recipient, "category": category,
                              "message": message.strip()[:1000], "visibility": visibility, "points": pts,
                              "sender_employee": emp.name,
                              "status": "Pending" if cint(s.recognition_requires_approval) else "Approved"})
        doc.insert(ignore_permissions=True)
        return {"doctype": doc.doctype, "name": doc.name, "status": doc.status}

    return run_once(client_request_id, "recognition", do)


@frappe.whitelist(methods=["POST"])
def react(name, reaction):
    guard("enable_recognition", employee=False)
    if reaction not in REACTIONS:
        frappe.throw(_("Invalid reaction"))
    rec = frappe.get_doc("ESS Recognition", name)
    from thinknxg_ess_portal.permissions import recognition_has_permission
    if not recognition_has_permission(rec, "read"):
        frappe.throw(_("Not found"), frappe.DoesNotExistError)
    existing = frappe.db.get_value("ESS Recognition Reaction", {"recognition": name, "user": frappe.session.user,
                                                                 "reaction": reaction})
    if existing:
        frappe.delete_doc("ESS Recognition Reaction", existing, ignore_permissions=True)
        return {"active": False}
    frappe.get_doc({"doctype": "ESS Recognition Reaction", "recognition": name, "user": frappe.session.user,
                    "reaction": reaction}).insert(ignore_permissions=True)
    return {"active": True}


@frappe.whitelist(methods=["GET"])
def team_summary():
    guard("enable_recognition", employee=False)
    team = identity.team_employees()
    if not team:
        frappe.throw(_("Team summary is for managers"), frappe.PermissionError)
    from thinknxg_ess_portal.services.analytics import suppress
    rows = frappe.db.sql("""select category, count(*) n from `tabESS Recognition` where recipient in %(t)s
        and status='Approved' and creation>=%(since)s group by category""",
                         {"t": team, "since": frappe.utils.add_months(today(), -3)}, as_dict=True)
    no_recognition = frappe.db.sql("""select count(*) from `tabEmployee` e where e.name in %(t)s and not exists
        (select 1 from `tabESS Recognition` r where r.recipient=e.name and r.status='Approved'
         and r.creation>=%(since)s)""", {"t": team, "since": frappe.utils.add_months(today(), -3)})[0][0]
    return {"by_category": rows, "team_size": len(team), "not_recognised_90d": no_recognition}


@frappe.whitelist(methods=["GET"])
def moderation_queue():
    guard("enable_recognition", employee=False)
    if not identity.is_hr():
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return frappe.get_all("ESS Recognition", filters={"status": "Pending"},
                          fields=["name", "sender_name", "recipient_name", "category", "message", "points", "creation"])


@frappe.whitelist(methods=["POST"])
def moderate(name, action):
    guard("enable_recognition", employee=False)
    if not identity.is_hr():
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    doc = frappe.get_doc("ESS Recognition", name)
    doc.status = "Approved" if action == "approve" else "Rejected"
    doc.moderated_by = frappe.session.user
    doc.save(ignore_permissions=True)
    return {"name": name, "status": doc.status}
