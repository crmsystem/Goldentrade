# Zoho CRM Account Audit — Requirements & Consultant Playbook

**Golden Trade Solutions · Zoho Authorized Partner**
Version 1.0 · 20 August 2026

This document has two halves.

- **Part A — Requirements.** What must be true, granted, signed and collected *before* an auditor logs in. Send the client-facing extract of this to every prospect.
- **Part B — Method.** What the consultant actually does once inside, domain by domain, with exact navigation paths, validated COQL queries, and what "good" looks like.

Every API call and query in Part B was executed against a live Zoho One Enterprise org before publication. Where Zoho behaved differently from the documentation, that is called out.

---
---

# PART A — REQUIREMENTS

## A1. Decide which audit you are selling

Scope creep is the main way a free audit turns into an unpaid week. Fix the tier before you book.

| | **Triage** | **Standard audit** | **Deep audit** |
|---|---|---|---|
| Duration | 30 minutes, live | 1–2 days | 5–10 days |
| Price | Free (lead magnet) | Fixed fee | Fixed fee |
| Access needed | Screen-share only | Named admin user | Named admin user + API + sandbox |
| Domains covered | 3 (users, data quality, automation) | All 10, evidence-light | All 10, evidence-complete |
| Output | 1-page summary, 3 findings | Findings report + scored workbook | Report + workbook + remediation plan + effort estimate |
| Data extracted | None | Metadata + aggregates | Metadata + aggregates + record samples |

The free 30-minute audit on the signup page is **Triage**. Do not promise more than three findings and a written summary; that is what converts, and it is deliverable in the time.

---

## A2. Access requirements

There are three legitimate ways to get in. Pick one and write it into the engagement letter.

### Option 1 — Named administrator user (recommended for Standard and Deep)

The client creates a **new, named user** for the auditor — never a shared login, never the client's own credentials.

- Setup → Users and Control → **Users** → New User
- Email: a real, individual auditor address (e.g. `auditor@goldentrade.solutions`)
- Profile: **Administrator**
- Role: **CEO** (or the top of the hierarchy) — anything lower and role-based sharing will silently hide records from you, and you will audit a partial picture without knowing it
- Enable two-factor authentication on the account before first login

**Why a named user:** every action is attributed to you in the audit log, so the client can see exactly what you did. A shared login destroys that and is a finding in its own right.

**Licence cost:** this consumes one CRM user licence for the duration. Check the client has a spare — Setup → General → **Company Details** shows purchased vs used. If they are at their limit, they must either free one up or buy one for the engagement. Say this out loud before the kickoff; a surprise licence purchase on day one poisons the relationship.

**Removal:** deactivate the user on the last day of the engagement and confirm it in writing. Put a calendar reminder on it — a partner login left active for two years is exactly the kind of finding you will be writing up about *someone else*.

### Option 2 — Read-only auditor profile (least privilege)

Where the client's security policy forbids handing a partner admin rights, build a custom profile instead.

- Setup → Users and Control → Security Control → **Profiles** → Clone the Administrator profile → name it `External Auditor`
- Remove every **create, edit, delete, mass update, mass delete, import and export** permission
- Keep: **View** on all modules, and all of **Setup / Customization / Automation / Users and Control / Data Administration** view rights
- Keep **Export** only if the client agrees — without it you cannot pull the audit log or record samples, and the audit becomes observational

**The trade-off is real.** A read-only profile is safer for the client and weaker for you: you cannot reproduce a broken workflow in place, and several diagnostic screens in Zoho only render for users who could act on them. Standard audits work fine this way. Deep audits do not.

### Option 3 — API read-only access (best for evidence, essential for Deep)

For repeatable, evidence-backed checks, use the API rather than clicking through screens. Register a **Self Client** — a server-to-server OAuth client with no redirect URI, which is the correct choice for an auditor's own tooling.

1. Client (or you, in their org) goes to `api-console.zoho.com` → **Self Client** → Create
2. Generate a grant token with a read-only scope set and a short validity (10 minutes is enough; the refresh token that follows is long-lived)
3. Exchange the grant token for a refresh token, and store the refresh token in your own secret manager — **not** in the audit workbook

Scopes follow the pattern `ZohoCRM.<category>.<operation>`. The read-only set that covers this playbook:

```
ZohoCRM.org.READ
ZohoCRM.users.READ
ZohoCRM.settings.READ
ZohoCRM.modules.ALL          (READ-only variants exist per module, e.g. ZohoCRM.modules.leads.READ)
ZohoCRM.coql.READ
ZohoCRM.bulk.READ
```

Confirm the exact strings in the API console when you generate the token — Zoho's scope list changes between API versions, and a scope that does not exist fails silently at token-exchange time rather than at call time.

**Data residency matters.** The API domain differs by the org's data centre: `zohoapis.com` (US), `.eu`, `.in`, `.com.au`, `.jp`, `.ca`, `.sa`. Using the wrong one returns an authentication error that looks like a bad token and wastes an hour. Check the org's domain before you start.

### Option 4 — Support Access (do NOT rely on this)

Zoho CRM has a **Support Access** feature at Setup → Security Control → Support Access. It grants temporary admin-level access with an expiry date, and it is frequently suggested by clients as "the secure way to let you in".

It is not built for partners. It is designed for **Zoho's own support agents**, only one support user can hold it at a time, and it blocks more than thirty operations including **export, integration access and security settings changes**. An audit that cannot export the audit log or read integration configuration is not an audit. Explain this politely and go back to Option 1 or 2.

### Access to the wider Zoho One suite

If the client runs Zoho One (most do), CRM does not exist in isolation. Request read access to whichever of these the CRM touches, because the worst findings usually live at the seams:

- **Zoho Directory / Admin Panel** — SSO, user provisioning, app assignment
- **Zoho Flow** — cross-app automations that silently write to CRM
- **Zoho Campaigns / Marketing Automation** — the other system creating and updating Leads
- **Zoho Desk, Books, Recruit, Creator, SalesIQ** — whichever are integrated
- **Zoho Analytics** — where the reporting truth actually lives, if they use it

---

## A3. Commercial and legal prerequisites

Do not skip these because the audit is free. The free tier is where you have *least* protection.

| Requirement | Why | Who signs |
|---|---|---|
| **Mutual NDA** | You will see pipeline, pricing and customer PII | Both |
| **Data Processing Agreement** | If any personal data leaves their tenancy — and it does, the moment you export a sample — you are a processor under GDPR / the PH Data Privacy Act | Both |
| **Written scope & access letter** | States which org, which modules, what you may and may not touch, and the access end date | Client admin |
| **Named client sponsor** | One person who can answer "why is it built like this?" and approve access | Client |
| **Read-only undertaking** | Your written commitment to change nothing without approval | You |
| **Change freeze (Deep audits)** | No config changes during the evidence window, or your findings describe a system that no longer exists | Client |

**PII handling rule.** Default to *no record export at all*. Aggregate counts answer almost every data-quality question — the queries in Part B are built to return counts, not rows. If you must pull a sample, mask it, keep it inside your own tenancy, and delete it when the report is signed off.

---

## A4. Pre-audit intake — collect before you log in

Half the findings in a good audit come from the gap between what the business says it does and what the CRM does. You cannot see that gap from inside the CRM alone.

**Business context**

1. What does the company sell, and what is the average deal size and sales cycle length?
2. How many salespeople, in how many teams, in how many countries?
3. Where do leads come from, ranked by volume? (Website, Facebook, WhatsApp, referral, outbound, events)
4. Describe the sales process in stages, as the team actually runs it — not as it is drawn in the CRM
5. What must never happen? (e.g. two reps calling one lead; a discount above X% without approval)
6. What reports do the leadership team look at weekly, and do they trust them?

**System context**

7. Which Zoho apps are in use, and which are integrated with CRM?
8. Which non-Zoho systems read from or write to CRM?
9. Who built the current setup — internal, a previous partner, or nobody in particular?
10. When was it last reviewed, and what changed?
11. Is there a sandbox? Is there documentation? (The answer is usually no and no. That is finding zero.)

**Pain**

12. What made you ask for this audit *now*?
13. What has someone already tried to fix, and why did it not stick?

Question 12 determines the shape of the report. An audit commissioned because "leads go missing" is a different document from one commissioned because "the board doesn't believe the forecast".

---

## A5. Auditor's toolkit

- Admin access per A2, and API credentials for Deep audits
- The scoring workbook (`zoho-crm-audit-checklist.xlsx`) open in a second window
- Screen recording running, with the client's written consent — you will misremember what you saw on screen 40
- A screenshot folder per domain, named `D3-fields-leads-01.png` so evidence maps to findings
- The client's own reports, exported to PDF on day one, so you can prove what the numbers said before anything changed

---
---

# PART B — THE AUDIT METHOD

Ten domains. Work them in order: the later ones only make sense once you know who the users are and what the data model looks like.

Every domain below gives you: **where to look**, **what good looks like**, and **the red flags that become findings**.

---

## D1 · Organization, edition and licensing

**Where:** Setup → General → **Company Details** · Setup → **Subscription** · API `GET /org`

**Check**

- Edition and renewal date. Half of all "Zoho can't do that" complaints are edition limits, not product limits.
- Licences **purchased vs active users**. Unused licences are the single easiest money-back finding in any audit.
- Base currency, multi-currency, time zone, fiscal year start, business hours.
- Data centre / domain, for API and compliance purposes.

**Good looks like:** licence count within one or two of active users; time zone and fiscal year match the operating business; currency settings match how they actually sell.

**Red flags**

- More than ~20% of licences unassigned (money on fire, and every month it renews)
- Fiscal year left at January when the business runs April–March — every forecast and target report is silently wrong
- Time zone set to the CRM buyer's location rather than the sales team's — date-stamped SLAs and "created today" views drift by a day

> **Live example.** In the org used to validate this playbook: 6 licences purchased, **1 active user**, 2 deleted and 1 disabled. That is 5 licences funding nothing — worth surfacing in the first five minutes of a triage call, because it is a number the client can act on the same afternoon.

---

## D2 · Users, roles, profiles and security model

**Where:** Setup → Users and Control → **Users / Roles / Profiles / Groups** · Security Control → **Data Sharing Settings**, **Login History**, **Audit Log**

**Check**

- Every user's **status** (active / disabled / deleted), **profile**, **role**, and last login
- How many people hold the **Administrator** profile
- The **role hierarchy** — does it mirror who reports to whom?
- **Organisation-wide default sharing** per module, and the sharing rules layered on top
- Territory management, if enabled
- Two-factor authentication and any SSO enforcement
- Login History for logins from unexpected countries or long-dormant accounts

**Good looks like:** two administrators (one primary, one break-glass); roles matching the org chart; org-wide default set to **Private** with deliberate sharing rules above it; every active user logged in within the last 30 days.

**Red flags**

- **Everyone is an administrator.** The most common serious finding in SME Zoho orgs. It makes the audit log useless and puts deletion rights in every hand.
- **Org-wide default set to Public Read/Write.** This is not merely permissive — it *switches off* role hierarchy and sharing rules entirely. If the client believes reps can only see their own leads, and the default is public, that belief is false and every "data privacy" assurance built on it is false too.
- Role and profile mismatched — a user on the **CEO** role with a **Standard** profile, or vice versa. Usually means someone was cloned from the wrong template and nobody noticed.
- Deleted or disabled users still owning live records (see D4 — orphaned records)
- Shared logins, generic addresses (`sales@`, `info@`) as CRM users, or an active partner/contractor account from a finished engagement
- 2FA not enforced

> **Live example.** The validation org had two accounts holding the **Administrator** profile — one of them a service account named "Parking System" — and a user carrying the **CEO** role on a **Standard** profile. Both are ordinary findings that take thirty seconds to spot and would take a client months to notice.

---

## D3 · Data model — modules, fields, layouts

**Where:** Setup → Customization → **Modules and Fields**, **Layouts**, **Global Sets**, **Templates** · API `GET /settings/modules`, `GET /settings/fields?module=X`

**Check**

- Which modules are active, which are custom, which standard modules are switched off
- Per key module: total fields, **used vs unused** fields, mandatory fields, unique fields, encrypted fields
- Layouts and layout rules; how many layouts per module and whether they are all in use
- Picklist values per field — count them, and read them
- Validation rules and duplicate-check fields
- Naming conventions on custom fields and modules

**Good looks like:** field count justified by the sales process; every mandatory field genuinely required at the point it is asked for; picklists short and mutually exclusive; a visible naming convention.

**Red flags**

- **Picklist sprawl.** Marketing sources, job-board sources and partner names all crammed into one `Lead Source` picklist. It makes attribution reporting impossible, and it is invisible until you count the values.
- Large numbers of fields with no data in them — built for a process that never launched
- Mandatory fields that reps cannot know at data-entry time, which is what drives junk values like "TBC" and "."
- Two fields meaning the same thing (`Mobile`, `Mobile_Number`, `Cell`) — a merge waiting to happen
- Custom modules used where a standard module with its built-in automation would have worked
- **No duplicate-check field configured** on Leads, Contacts or Accounts

> **Live example.** The validation org's `Lead Source` field carried **25 distinct values**, mixing sales channels (Partner, Facebook, Google AdWords) with recruitment job boards (Jooble, Jora, neuvoo, Recruit.net, CareerSite). Two different business processes are sharing one picklist. No attribution report built on that field can be trusted.

---

## D4 · Data quality

This is where the client feels the pain, so it is where the audit earns its fee. Work in aggregates — you rarely need to see a single record.

**Where:** COQL via API, or Setup → Data Administration → **Deduplicate Records**, **Data Backup**, **Storage**

**Measure, per key module**

| Metric | Why it matters |
|---|---|
| Total records | Baseline, and a storage-cost input |
| % missing email **and** phone | Uncontactable records — the true size of the usable database |
| % missing owner, or owned by an inactive user | Orphaned work nobody is doing |
| % missing the primary segmentation field (Lead Source, Industry, Status) | Determines whether reporting is even possible |
| % not modified in 6 / 12 / 24 months | Stale mass; a candidate for archive |
| Duplicate rate on email and on company name | The number the client already suspects and cannot prove |
| Records created by integration vs by hand | Tells you which inbound channel is polluting the database |

**Good looks like:** under 5% missing on any field the business actually reports on; duplicate rate under 2%; stale records archived rather than accumulating.

**Red flags**

- A large null population on a field the business reports on weekly
- More stale than active records — the CRM has become an archive with a sales UI
- Duplicates concentrated in one lead source, which localises the fix to one integration
- Storage approaching the plan limit, driven by attachments rather than records

> **Live example.** In the validation org: **1,658 of ~5,857 leads (≈28%) had no Lead Source at all**, and **4,511 leads had not been modified in over twelve months** — 3,706 of those carrying no Lead Status either. A weekly "leads by source" report in that org is describing roughly seven records in ten, and is silently omitting the rest.

---

## D5 · Sales process — pipelines, stages, blueprint

**Where:** Setup → Customization → **Pipelines** · Automation → **Blueprint** · Modules → Deals → Stage field

**Check**

- Number of pipelines, and whether each maps to a real, distinct sales motion
- Stage names — are they **buyer** milestones or **seller** activities? ("Proposal sent" is a seller activity; "Customer has budget approved" is a buyer milestone. The second forecasts; the first does not.)
- Stage probability values and whether anyone has ever revisited them
- Blueprint: is one configured, is it enforced, does it have escape hatches
- Closed-lost reason capture
- Lead → Deal conversion mapping — which fields carry across, and which are silently dropped

**Good looks like:** one pipeline per genuinely different sales motion; 5–7 stages; exit criteria per stage that two different reps would apply the same way; mandatory closed-lost reason.

**Red flags**

- Ten-plus stages — reps will park deals in whichever stage avoids scrutiny
- Probabilities at default (10/20/40/60/80) with no basis in the client's own conversion history, feeding a forecast the board is asked to believe
- No closed-lost reason, so the company cannot learn anything from losing
- Conversion mapping dropping fields, so context collected on the Lead vanishes at the moment of conversion — a very common cause of "the data disappeared"

---

## D6 · Automation

**Where:** Setup → Automation → **Workflow Rules**, **Assignment Rules**, **Scoring Rules**, **Schedules**, **Approval Processes**, **Case Escalation** · Functions → **Custom Functions** · Setup → **Webhooks**

**Check**

- Every active rule: name, module, trigger, criteria, actions, **execution order**
- Whether rule names describe their purpose (`WF_Lead_Assign_WhatsApp_RoundRobin`) or not (`Rule 1 copy copy`)
- Assignment rules and their order — Zoho evaluates in sequence and **stops at the first match**
- Custom functions: are they version-controlled anywhere outside Zoho? Do they have error handling?
- Webhook failure logs
- Time-based / scheduled actions still pointing at people who left
- Rules per module against the edition's limit

**Good looks like:** every rule named, owned and documented; assignment logic understood by the sales manager; functions stored in a repository outside Zoho; failure notifications routed to a monitored inbox.

**Red flags**

- Rules that no living person can explain
- **Assignment rule order producing silent misrouting** — the single most common cause of "our WhatsApp leads never get assigned". The rule is fine; an earlier rule matched first and stopped evaluation.
- Two rules writing to the same field on the same trigger — last writer wins, non-deterministically from the user's point of view
- Custom functions with no error handling, failing quietly
- Webhooks failing for months with nobody notified
- Deluge written directly in production with no sandbox copy and no source control

---

## D7 · Integrations and API health

**Where:** Setup → Marketplace → **All / Installed** · Developer Space → **APIs, Connections, Webhooks, Functions** · Zoho Flow console · Setup → **API Usage / Limits**

**Check**

- Every installed extension and connected app; who owns each connection and whether that person still works there
- Which system is the **source of truth** for each shared object — and whether both sides believe they are
- API call consumption against the daily limit, and the trend
- Failure and retry behaviour on each integration
- Zoho Flow flows writing into CRM (these bypass CRM's own automation view entirely and are easy to miss)
- Any integration authenticated as a *person* rather than a service account

**Good looks like:** each integration documented with direction, frequency, field mapping and owner; service-account authentication; API usage under 60% of limit; failures alerting someone.

**Red flags**

- Integration authenticated by a departed employee's OAuth token — it dies the day IT closes their account, and no one will connect the outage to the cause
- Bidirectional sync with no conflict rule, quietly overwriting in both directions
- API usage above 80% of daily limit — you are one campaign away from a hard stop
- Duplicate creation traced to an integration that matches on the wrong key

---

## D8 · Reporting and analytics

**Where:** Reports tab · Analytics / Dashboards · Setup → **Forecasts**

**Check**

- Number of reports, and how many have been run in the last 90 days
- Whether leadership's weekly numbers come from CRM, from Analytics, or from a spreadsheet somebody maintains by hand
- Forecast configuration: targets set, period alignment, hierarchy
- Whether report filters silently exclude records with null values in the fields found broken in D4

**Good looks like:** a small set of used reports; one agreed source for each leadership number; forecast built on validated stage probabilities.

**Red flags**

- Hundreds of reports, a handful ever opened — nobody trusts them, so everyone builds their own
- **The real reporting happens in a spreadsheet.** This is the clearest possible signal that the CRM has failed at its job, and it is worth stating that plainly in the report.
- Reports whose totals disagree with each other, usually because of null-handling in filters

---

## D9 · Adoption

Configuration findings are cheap. Adoption findings are what actually changes the client's revenue.

**Where:** Setup → Security Control → **Login History** · Audit Log · per-user activity reports

**Measure**

- Logins per user per week over 90 days
- Records created and modified per user
- Activities (calls, meetings, emails) logged per rep per week
- Time between record creation and first touch
- Mobile app usage
- % of deals with a next activity scheduled

**Good looks like:** daily logins from every rep; activity logging in line with what the team says it does; a next step scheduled on the large majority of open deals.

**Red flags**

- Reps logging in weekly, not daily — the CRM is a reporting chore, not a working tool
- Data entry clustered on Friday afternoons — retrospective invention, not record-keeping
- Managers running the whole pipeline from exports
- Open deals with no next activity — the pipeline is a list, not a plan

---

## D10 · Governance, compliance and continuity

**Where:** Setup → Data Administration → **Data Backup**, **Export**, **Storage** · Security Control → **Audit Log**, **Compliance Settings** · Setup → **Sandbox**

**Check**

- Backup: is one scheduled, where does it land, when was a **restore** last tested?
- Audit log: enabled, reviewed by anyone, exportable
- Sandbox: does one exist, is it used before production changes
- Compliance settings (GDPR / data privacy), consent capture, data-subject request process
- Data retention policy — what gets deleted, when, and who decided
- Documentation of the configuration
- Change management: who may change what, and is it recorded

**Good looks like:** scheduled backup with a tested restore; sandbox-first change process; audit log reviewed quarterly; a named CRM owner; written retention policy.

**Red flags**

- **No backup, or a backup nobody has ever restored.** An untested backup is a belief, not a control.
- No sandbox on a paid edition that includes one — every change is a production experiment
- No named owner. When nobody owns the CRM, every finding in this report regenerates within eighteen months of you fixing it.
- Personal data retained indefinitely with no policy

**Audit log retention:** Zoho CRM keeps audit log entries for **up to 3 years**; anything older is permanently deleted. Administrators and CEO-role users see the whole org; other users see only themselves and their subordinates. Export from Setup → Security Control → Audit Log → *Export Audit Log* (CSV), filterable by entity, user, action type and date range. **Login history is not in the audit log** — it lives at Setup → Security Control → Login History.

---
---

# PART C — QUERY PACK

Validated against Zoho CRM API v8 COQL. Run via `POST /crm/v8/coql` or the Query Workbench (Setup → Developer Space → Query Workbench).

### Four COQL rules learned the hard way

1. **A `WHERE` clause is mandatory.** A bare `select ... from Leads limit 5` fails with `SYNTAX_ERROR: missing clause`. When you have no real filter, use `where id is not null`.
2. **Only queryable fields work.** `Phone` on Leads returns `INVALID_QUERY: column given seems to be invalid`. Confirm field API names with `GET /settings/fields?module=Leads` before writing queries — do not assume the label matches the API name.
3. **`HAVING` is not supported.** A `group by … having COUNT(id) > 1` runs without error but **ignores the HAVING clause and returns groups of 1**. This silently produces a wrong duplicate report. Do duplicate detection with Zoho's built-in Deduplicate Records tool, or export and group externally.
4. **Aggregates with `GROUP BY` do work** — `COUNT()`, `SUM()`, `MIN()`, `MAX()`, `AVG()`. This is how you get every number in D4 without exporting a single personal record.

### D1 — record volume by module

```sql
select COUNT(id) from Leads where id is not null
```
Repeat for Contacts, Accounts, Deals, Tasks.

### D3 — picklist sprawl

```sql
select Lead_Source, COUNT(id) from Leads
where id is not null group by Lead_Source
```
Count the rows returned. More than about a dozen values on a segmentation field is a finding.

### D4 — uncontactable records

```sql
select COUNT(id) from Leads where Email is null
```
```sql
select COUNT(id) from Contacts where Email is null and Mobile is null
```

### D4 — null segmentation field

```sql
select Lead_Source, COUNT(id) from Leads
where Lead_Source is null group by Lead_Source
```

### D4 — stale records (adjust the date and offset to the org's time zone)

```sql
select Lead_Status, COUNT(id) from Leads
where Modified_Time < '2025-08-20T00:00:00+08:00'
group by Lead_Status
```

### D4 — ownership distribution and orphans

```sql
select Owner, COUNT(id) from Leads
where id is not null group by Owner
```
Cross-reference every owner ID against `GET /users?type=ActiveUsers`. Any owner not on that list is holding orphaned records.

### D5 — pipeline shape

```sql
select Stage, COUNT(id), SUM(Amount) from Deals
where id is not null group by Stage
```

### D5 — deals with no close date, or a close date in the past

```sql
select COUNT(id) from Deals where Closing_Date < '2026-08-20'
and Stage not in ('Closed Won','Closed Lost')
```
Overdue open deals are the fastest measure of forecast hygiene there is.

### Supporting metadata calls

| Purpose | Call |
|---|---|
| Org, edition, licences | `GET /org` |
| Users, profiles, roles, status | `GET /users?type=AllUsers` |
| Module inventory | `GET /settings/modules` |
| Field inventory (used vs unused) | `GET /settings/fields?module=Leads&type=unused` |
| Layouts | `GET /settings/layouts?module=Leads` |
| Workflow rules | `GET /settings/automation/workflow_rules` |
| Assignment rules | `GET /settings/automation/assignment_rules` |
| Webhooks and their failures | `GET /settings/webhooks`, `GET /settings/webhooks/failures` |
| Org variables | `GET /settings/variables` |
| Territories | `GET /settings/territories` |

---
---

# PART D — SCORING, REPORTING AND DELIVERY

## D-1. Severity model

Rate every finding on business impact, not technical elegance.

| Severity | Definition | Example | Expected response |
|---|---|---|---|
| **Critical** | Losing revenue, breaking a legal obligation, or risking data loss *right now* | No backup ever tested; org-wide sharing public when reps are told it is private | Fix this week |
| **High** | Materially degrading a core process | Assignment rules misrouting an entire lead channel; 28% of leads with no source | Fix this month |
| **Medium** | Friction, waste, or unreliable reporting | Picklist sprawl; unused licences; 200 unused fields | Fix this quarter |
| **Low** | Hygiene and future-proofing | Naming conventions; undocumented rules | Fix opportunistically |

A finding is only Critical if you can name what breaks and who feels it. "Best practice says otherwise" is Low.

## D-2. Scoring

The workbook scores each of the ten domains 0–5 and weights them:

| Domain | Weight | Rationale |
|---|---|---|
| D4 Data quality | 20% | Everything downstream depends on it |
| D2 Users & security | 15% | Risk and access correctness |
| D6 Automation | 15% | Where process actually lives |
| D5 Sales process | 10% | Forecast credibility |
| D9 Adoption | 10% | Determines whether any of it matters |
| D3 Data model | 10% | Constrains everything else |
| D10 Governance | 8% | Continuity and compliance |
| D7 Integrations | 6% | Failure blast radius |
| D8 Reporting | 4% | Symptom more than cause |
| D1 Org & licensing | 2% | Quick wins, low structural weight |

Weighted total → **CRM Health Score /100**. Bands: 80+ healthy, 60–79 workable with gaps, 40–59 significant remediation, under 40 rebuild the foundations before adding anything.

Publish the weights with the score. A score whose derivation is hidden reads as a sales instrument, because that is usually what it is.

## D-3. Findings report structure

1. **Executive summary** — one page, plain language, no jargon. Three sentences on the state of the system, the health score, and the three things to do first.
2. **Scorecard** — the ten domains, scored, with the weighting shown.
3. **Critical and High findings** — one page each: what we found, the evidence (screenshot or query result), the business impact in the client's own terms, the recommended fix, and the effort estimate.
4. **Medium and Low findings** — table form.
5. **Remediation roadmap** — sequenced into Now / Next / Later, with dependencies marked. Sequence matters: fixing data quality before fixing the fields that caused it means doing the work twice.
6. **What is working well.** Not padding. It protects what is good from being "improved" in a later phase, and it makes the criticism credible.
7. **Appendix** — access used, dates, methodology, query pack, and the limitations of the audit.

**Always state limitations.** "We reviewed configuration and aggregate data. We did not test every workflow end to end, and we did not review Zoho Flow, which was out of scope." An audit that implies completeness it does not have is the one that gets quoted back at you.

## D-4. Time budget — Standard audit (2 days)

| | Activity |
|---|---|
| Day 1 AM | D1, D2, D3 — org, users, data model |
| Day 1 PM | D4 — data quality queries; D5 — pipeline |
| Day 2 AM | D6, D7 — automation and integrations |
| Day 2 PM | D8, D9, D10; scoring; draft report |
| +3 days | Write-up, internal review, presentation |

For the **free 30-minute triage**, run only: licences vs active users (D1), administrator count and org-wide sharing (D2), null rate on the primary segmentation field (D4), and assignment rule order (D6). Those four checks produce a credible finding in almost every org, and they fit the time.

## D-5. Common mistakes auditors make

- **Auditing against best practice instead of against the business.** Twelve pipeline stages is wrong for a transactional SME and right for a complex enterprise sale. Ask before you judge.
- **Confusing "unused" with "useless".** A field with no data may be feeding an integration or a rule. Check before recommending deletion.
- **Reporting configuration and ignoring adoption.** A perfectly configured CRM nobody opens scores well and delivers nothing.
- **Auditing without a change freeze, then presenting findings the client has already fixed.** It undermines everything else in the room.
- **Burying the finding the client already suspects.** They asked for the audit for a reason. If your report does not address question 12 from the intake, it does not matter how thorough the rest is.
- **Turning the audit into a sales pitch.** The audit is the product. If it is good, the project follows. If every finding conveniently requires your services, the client will notice.

---

## Reusable client-facing request (copy into an email)

> To run your CRM audit we need, before the session:
>
> 1. A named administrator user created for our auditor (Administrator profile, top-level role), with 2FA enabled — we will confirm in writing when it can be removed.
> 2. Confirmation of a spare user licence, or your agreement that one will be freed for the engagement.
> 3. A signed mutual NDA and data processing agreement.
> 4. One named sponsor who can answer "why is it built this way?"
> 5. Read access to any Zoho apps integrated with CRM — commonly Flow, Campaigns, Desk and Analytics.
> 6. Answers to the 13 intake questions attached.
>
> We will change nothing without your written approval, we will not export personal data unless you ask us to, and every action we take is recorded in your own audit log for you to review.

---

*Prepared by Golden Trade Solutions. API behaviour, retention periods and navigation paths verified against a live Zoho One Enterprise org on 20 August 2026. Zoho changes its interface regularly — re-verify navigation paths before each engagement.*
