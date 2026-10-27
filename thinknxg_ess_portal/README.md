# thinkNXG ESS Portal

Enterprise Employee Self-Service for **thinkNXG HR (Frappe HR v16)** — a Vue 3 + TypeScript PWA served at `/ess` by a custom Frappe app, for employees, managers and HR.

The portal is an experience layer. Attendance, leave, payroll, expenses, performance and workflows stay in Frappe HR; the app never re-implements leave maths, payroll or accounting. Custom DocTypes exist only for capabilities HRMS doesn't have (helpdesk, letters, recognition, AI audit, policies, delegation).

```
Vue 3 PWA (/ess)  ──  Router guards, Pinia, in-memory server cache, offline queue
        │  same-origin session + CSRF, no API keys in the browser
Frappe API layer  ──  thinknxg_ess_portal.api.*  (identity → scope → validation → idempotency → audit)
        │
Native HRMS       ──  Employee, Checkin, Attendance(+Request), Leave Application/Allocation/Ledger,
                      Salary Slip, Expense Claim, Employee Advance, Shift Request, Goal, Appraisal, Training
Custom ESS        ──  29 DocTypes in module "ESS Portal"
Infra             ──  MariaDB · Redis (cache, rate limits, AI transcripts) · RQ jobs · scheduler · private files
```

## Install

```bash
cd frappe-bench
bench get-app /path/to/thinknxg_ess_portal        # or your git remote
bench --site your.site install-app thinknxg_ess_portal
bench --site your.site migrate
bench build --app thinknxg_ess_portal              # copies the prebuilt SPA into /assets
```

The zip ships with the frontend already built (`thinknxg_ess_portal/public/ess`, `www/ess.html`), so Node is not needed on the server. To rebuild:

```bash
cd apps/thinknxg_ess_portal/frontend
npm ci && npm run build        # type-check, Vite build, writes www/ess.html, stamps the service worker
npm run dev                    # http://localhost:8080/ess, proxies /api to FRAPPE_URL (default :8000)
npm test                       # Vitest
```

Requires `frappe`, `erpnext`, `hrms` (v16). Optional: `pip install pypdf` (index PDF policies), `pywebpush` (push notifications).

**After install**
1. Assign roles: `ESS Portal Admin`, `ESS HR Agent`, `ESS Payroll Officer`, `ESS Department Head` (created on install). Set *ESS Department Head* on Department records if department heads need team scope.
2. Open **ESS Portal Settings**: brand, module toggles, attendance rules, SLA defaults, AI provider + key, VAPID keys.
3. Add **ESS Knowledge Source** records (policies/FAQs) for the assistant; edit the two seeded **ESS Document Templates** and set a Letter Head.
4. Seeded: 7 helpdesk categories (incl. confidential *Payroll & Salary*, *Visa & Residency*), 5 recognition values, 7 badges.

## Roles and scope

| Capability | Employee | Manager (derived) | HR User / HR Manager | ESS HR Agent | ESS Payroll Officer | ESS Portal Admin |
|---|---|---|---|---|---|---|
| Own profile, attendance, leave, payslips, expenses | ✔ | ✔ | ✔ | if employee | if employee | if employee |
| Team attendance, calendar, approvals | – | reporting line (recursive) + headed departments + active delegations | company scope / all | – | – | – |
| Other employees' payslips | – | – | HR Manager (audited) | – | ✔ (audited) | – |
| HR tickets | own | own | all | non-confidential + assigned | confidential + assigned | all |
| Generate letters | eligible templates | eligible | approve per template role | – | – | ✔ |
| Analytics | own | team aggregates | HR scope, k-anonymised | – | – | – |
| Portal configuration, AI sources, audit trail | – | – | – | – | – | ✔ |

"Manager" is never a role check — it is derived per request from `Employee.reports_to` (recursive) and `Department.ess_department_head`. Every API derives identity from `frappe.session.user`; no endpoint accepts an employee id for the caller's own data. Router guards only shape navigation.

Record-level rules for custom DocTypes are enforced in `permissions/__init__.py` via `permission_query_conditions` and `has_permission`, so Desk and `/api/resource` cannot widen access either.

## API contracts (`/api/method/thinknxg_ess_portal.api.<module>.<fn>`)

| Module | Endpoints |
|---|---|
| `bootstrap` | `get_boot` |
| `dashboard` | `get_summary` |
| `inbox` | `get_items(cursor, limit, type)` → `{items[], total, next_cursor}` |
| `attendance` | `get_today`, `check_in`, `check_out`, `get_month`, `request_correction`, `my_corrections` |
| `leave` | `get_overview`, `preview`, `create_request`, `my_requests`, `withdraw_request`, `get_calendar` |
| `payroll` | `list_payslips`, `get_payslip`, `download_payslip`, `get_benefits` |
| `expenses` | `overview`, `create_claim`, `claim_detail`, `request_advance` |
| `profile` | `get_profile`, `request_change`, `save_employee_document` |
| `approvals` | `get_pending`, `get_detail`, `act`, `bulk_act`, `history`, `list_delegations`, `save_delegation`, `revoke_delegation`, `search_colleagues` |
| `team` | `get_overview`, `get_exceptions`, `get_member` |
| `helpdesk` | `categories`, `my_tickets`, `create_ticket`, `get_ticket`, `reply`, `reopen`, `rate`, `close`, `faqs` · agent: `queue`, `assign`, `set_status`, `set_priority`, `agents`, `canned_responses` |
| `documents` | `overview`, `request`, `cancel_request`, `download`, `admin_requests`, `regenerate` |
| `policies` | `list_mine`, `get_policy`, `acknowledge` |
| `announcements` | `list_announcements`, `mark_read`, `save_announcement`, `admin_list` |
| `recognition` | `feed`, `summary`, `give`, `react`, `team_summary`, `moderation_queue`, `moderate` |
| `goals` | `overview`, `update_goal_progress` |
| `analytics` | `employee`, `manager`, `hr` |
| `assistant` | `ask`, `confirm_action`, `feedback`, `conversations`, `suggestions` |
| `notifications` | `list_notifications`, `mark_read`, `get_preferences`, `set_preference`, `push_subscribe`, `push_unsubscribe` |
| `hr_admin` | `employee_search`, `employee_detail`, `verify_document`, `expiring_documents`, `get_settings`, `save_settings`, `save_knowledge_source`, `audit_events`, `ai_quality` |

All mutations accept `client_request_id`; `services/idempotency.run_once` records it in **ESS Offline Action**, so retries, double taps and offline replays never duplicate a request. Reads are GET-only, mutations POST-only.

## Custom DocTypes (module "ESS Portal")

Settings & ops: ESS Portal Settings · ESS Notification Preference · ESS Push Subscription · ESS Offline Action · ESS Audit Event · ESS Analytics Snapshot · ESS Approval Delegation
Helpdesk: ESS HR Ticket · ESS HR Ticket Comment · ESS HR Ticket Category · ESS Canned Response
Documents: ESS Document Template · ESS Document Request · ESS Employee Document (passport/resident card/visa/labour card with expiry)
Recognition: ESS Recognition · ESS Recognition Reaction · ESS Recognition Category · ESS Badge · ESS Badge Award
AI: ESS AI Conversation (metadata) · ESS AI Message Audit (no message text) · ESS Knowledge Source · ESS Knowledge Chunk
Comms: ESS Announcement · ESS Announcement Read · ESS Policy · ESS Policy Acknowledgement
Profile: ESS Profile Change Request · ESS Profile Change Item (child)

Custom fields: `Department.ess_department_head`, `Attendance Request.ess_status` / `ess_review_comment` (HRMS has no rejected state for drafts).

## How the key flows work

- **Check-in** — server time only; shift from active Shift Assignment (or default shift); geofence from HRMS *Shift Location* radius (haversine, tolerant of GPS accuracy up to 100 m); sequence + cooldown checks; never queued offline.
- **Leave** — balances from `get_leave_details`, days from `get_number_of_leave_days`, balance from `get_leave_balance_on`; overlap/holiday preview recalculated server-side on every date change and again at submit.
- **Approvals** — a request is actionable only if it is in the caller's computed pending list (approver field, reporting line, HR role, or active delegation). If a Frappe Workflow exists for the DocType, the matching workflow action is applied instead of setting status. Rejections require a reason. Every decision writes an ESS Audit Event.
- **Delegation** — hourly job shares open documents with the delegate and revokes on expiry.
- **Letters** — HR-authored Jinja templates (validated, versioned on change); employees pick a template, never fields or code. Eligibility (status, service months, monthly limit), optional approval by template role, PDF rendered in a background job, stored as a private File, verification code + public `/ess-verify` page (rate-limited, toggleable).
- **Helpdesk** — SLA due dates from category; transition map enforced in the controller; 15-minute escalation job (level 1 → category escalation user, level 2+ → HR Managers); internal notes never leave the server for employees; auto-close after N days.
- **Recognition** — monthly points budget per sender, optional HR moderation, no self-recognition, rule badges (anniversary, recognitions received/given, training, onboarding, policies). No rankings, nothing tied to hours or attendance.
- **Analytics** — server-side aggregates only; HR breakdowns below `min_group_size` (default 5) are suppressed; daily snapshot table for trend reporting.

## AI HR assistant

`services/assistant.py` → identity check → module/rate limit → deterministic refusal guard for other people's pay/personal data → redaction (IBAN, card/account numbers, emails, phones) → model with **allow-listed tools** → proposal.

- Tools (`services/ai_tools.py`) take **no identity arguments**; any `employee`/`user` argument a model invents is stripped. Data always comes from the session employee, so "show me Ahmed's payslip" cannot succeed even if the model tries.
- Policy answers come from BM25 retrieval over **ESS Knowledge Chunk**, filtered by audience/company/department *before* scoring, cited as [1], [2]. Retrieved text is labelled as data in the system prompt.
- Consequential actions (leave request, HR ticket) are returned as proposals held in Redis for 15 minutes; the employee confirms in a card, and the normal API (with validation and idempotency) runs.
- Payslip amounts are hidden from the model unless `ai_allow_salary_answers` is on.
- Providers: Anthropic Messages API or any OpenAI-compatible endpoint; key stored as a Password field, server-side only. With the provider *Disabled*, the assistant still works in deterministic mode (intent routing + policy excerpts + "raise a ticket" proposal).
- Audit stores metadata only (intent, tools, sources, outcome, latency, redaction count, feedback). Transcripts live in Redis for 24 h. Retention job purges metadata after `ai_retention_days`.

## PWA

Manifest + icons under `/assets/thinknxg_ess_portal/ess/`, service worker served from `www/ess-sw.js` with scope `/ess`. Hashed assets cache-first; navigation network-first with an offline page; `/api`, `/files`, `/private` are never cached. Leave requests, tickets and recognition can be queued offline (state shown as Queued → Submitted → Confirmed) and replay with the same request id; check-in and approvals require a live server confirmation. Web Push via VAPID (optional `pywebpush`); payloads carry only a title and route. Logout clears caches and the offline queue.

EN/AR with full RTL, light/dark/system themes, keyboard command palette (Ctrl/⌘ K), skip link, focus-trapped dialogs, reduced-motion support, touch-sized controls and a bottom tab bar with a centre punch button on mobile.

## Tests

- `thinknxg_ess_portal/tests/test_security.py` — colleague ticket isolation, confidential tickets hidden from agents, internal notes hidden, manager scope = reporting line, non-manager blocked from team member, unauthorised approval blocked, protected profile fields rejected, idempotent duplicate submission, assistant refusal for a colleague's payslip, AI tool identity stripping, self-recognition blocked.
  `bench --site test.site run-tests --app thinknxg_ess_portal`
- `frontend/tests/unit.spec.ts` — markdown XSS escaping and link allow-list, offline queue rules, format helpers (`npm test`).

## Notes and assumptions to verify on your bench

- Python package is `thinknxg_ess_portal` (Frappe requires the package to match the app name), so methods are `thinknxg_ess_portal.api.*` rather than `ess_portal.api.*`.
- Field names follow HRMS v16 and are guarded with `meta.has_field` where they vary (Checkin latitude/longitude, Shift Location, Overtime Slip, Employee Benefit Ledger, Goal, Onboarding). Confirm against your installed release and customisations.
- Expense claims are created as drafts with the company's default payable account; submission/payment stays with Accounts unless *Auto-submit approved expenses* is enabled. Employee Advance uses the company's default advance account.
- The UI uses its own lightweight component set rather than `frappe-ui`, to keep the build reproducible; it can be swapped in later without touching the API layer.
- Realtime events are published (`ess_notification`, `ess_ticket_update`); the SPA polls unread counts every 60 s and does not require socket.io.
