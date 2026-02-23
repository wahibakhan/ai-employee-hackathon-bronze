---
type: agent
agent_id: AG05
name: Daily Briefing Agent
version: 1.0
tier: silver
trigger: "Morning call / session start / explicit user request"
skills_used: [SK07]
chains_to: [AG03]
created: 2026-02-22
---

# AG05 — Daily Briefing Agent

## Description
Generates a structured, actionable daily briefing by reading the full vault
state. Counts tasks, surfaces priorities, highlights pending approvals, and
gives the human a clear "top 3 actions" to start the day. Always the first
agent to run in a new session.

Outputs a `Briefing_[date].md` file and updates the Dashboard — then hands
control to AG03 Task Orchestrator to execute the day's work.

---

## Trigger Conditions

- User says: `Activate Agent: Daily Briefing Agent`
- Session starts (first agent called by AG03 in morning)
- User says: `What's my status today?` or `Give me a briefing`
- Scheduled daily at session open (can be automated via cron in Gold Tier)

---

## Skills Chain

```
SK07 Dashboard Updater → refresh all counts before briefing
     (reads vault directly — no other skills needed for reading)
→ chains to AG03 Task Orchestrator after briefing is delivered
```

---

## Reasoning Loop (Iterate Until Complete)

```
LOOP START:

  ── ITERATION 1: VAULT SNAPSHOT ──────────────────────────
  READ    Needs_Action/ → list all .md files
  READ    Done/         → count files (completed today vs total)
  READ    Dashboard.md.md → last known state
  READ    Company_Handbook.md → any active rules or constraints

  COUNT:
    pending_total      = all .md in Needs_Action/
    emails_pending     = EMAIL_*.md files in Needs_Action/
    approvals_pending  = APPROVAL_*.md files in Needs_Action/
    plans_active       = Plan_*.md files in Needs_Action/
    drafts_ready       = EMAIL_DRAFT_*.md + LinkedIn_*.md in Needs_Action/
    done_today         = files in Done/ modified today
    done_total         = all files in Done/

  ── ITERATION 2: PRIORITY DETECTION ──────────────────────
  SCAN    each Needs_Action/ file's YAML frontmatter
  FLAG    CRITICAL items (priority: critical OR type: invoice/payment)
  FLAG    OVERDUE items (created > 48h ago and still pending)
  FLAG    APPROVAL items (status: awaiting_approval)
  SORT    by: CRITICAL → APPROVAL_overdue → HIGH → MEDIUM → LOW

  BUILD   top_3_actions:
    #1 = most critical/urgent task
    #2 = second priority or oldest unactioned item
    #3 = quick win (LOW effort, HIGH value)

  ── ITERATION 3: GENERATE BRIEFING ───────────────────────
  COMPOSE Briefing_[YYYY-MM-DD].md with sections:
    - Vault Health Summary (counts)
    - ⚠️ Items Needing Immediate Attention (CRITICAL + APPROVALS)
    - Today's Top 3 Actions
    - Full Pending Queue (sorted by priority)
    - Completed Yesterday / This Week
    - Suggested Agent to Run Next

  WRITE   to Needs_Action/Briefing_[date].md
  PRINT   condensed version to console / Dashboard

  ── ITERATION 4: DASHBOARD SYNC ──────────────────────────
  CALL    SK07 Dashboard Updater with fresh counts:
    Pending Tasks:      [n]
    Active Plans:       [n]
    Approvals Awaiting: [n]
    Completed Today:    [n]
    Last Update:        [timestamp]
    Overall Health:     [derived status]

  ── ITERATION 5: HAND OFF ────────────────────────────────
  IF pending_total > 0:
      RECOMMEND "Activate Agent: Task Orchestrator Agent to begin processing"
      CHAIN → AG03 Task Orchestrator (if auto-mode enabled)
  IF approvals_pending > 0:
      HIGHLIGHT "⚠️ [n] approval(s) need your attention before Claude can proceed"
  IF pending_total == 0:
      STATUS "All clear — vault is clean. Nothing pending."

LOOP END (single pass — briefing is one-shot)
```

---

## Output Format

**File:** `Needs_Action/Briefing_[YYYY-MM-DD].md`

```markdown
---
type: daily_briefing
status: delivered
date: [YYYY-MM-DD]
generated_at: [timestamp]
pending_count: [n]
approvals_pending: [n]
done_today: [n]
---

# 📋 Daily Briefing — [Day, Date]

---

## Vault Health

| Metric | Count |
|--------|-------|
| Pending Tasks | [n] |
| Emails to Triage | [n] |
| Approvals Awaiting | [n] |
| Active Plans | [n] |
| Drafts Ready for Review | [n] |
| Completed Today | [n] |
| Done (All Time) | [n] |

**Overall Health:** [Idle ✅ / Active 🔵 / Busy 🟡 / Attention Needed ⚠️]

---

## ⚠️ Immediate Attention Required

[List CRITICAL + APPROVAL items with one-line description each]
- `APPROVAL_payment-zara.md` — Payment approval pending 14h ⏰
- `EMAIL_18f3a.md` — Invoice query from client (CRITICAL)

*(Empty if nothing critical)*

---

## 🎯 Today's Top 3 Actions

1. **[Action 1]** — `[filename]` | Priority: CRITICAL
   → Suggested: Activate Agent: Approval Handler Agent

2. **[Action 2]** — `[filename]` | Priority: HIGH
   → Suggested: Activate Agent: Email Triage Agent

3. **[Action 3]** — `[filename]` | Priority: MEDIUM
   → Suggested: Activate Agent: Social Media Agent

---

## 📥 Full Pending Queue

| Priority | File | Type | Age |
|----------|------|------|-----|
| CRITICAL | APPROVAL_payment.md | approval | 14h |
| HIGH | EMAIL_18f3a.md | email | 2h |
| MEDIUM | LinkedIn_hackathon.md | social | 5h |
| LOW | EMAIL_newsletter.md | email | 1d |

---

## ✅ Completed

- Yesterday: [n] tasks moved to Done/
- This Week: [n] tasks total
- Last completed: `[filename]` at [timestamp]

---

## Suggested Next Step

```
Activate Agent: Task Orchestrator Agent
```

---
*Generated by AG05 Daily Briefing Agent — Panaversity AI Employee Silver Tier*
*[timestamp]*
```

---

## Example Invocation

```
Activate Agent: Daily Briefing Agent
```
*Full vault scan + briefing + dashboard sync*

```
What's my status today?
```
*Triggers Daily Briefing Agent automatically*

```
Activate Agent: Daily Briefing Agent with mode: quick
```
*Condensed version — counts + top 3 only, no full queue*

---

## Sample Dashboard Entry After Briefing

```markdown
### AG05 Daily Briefing — 2026-02-22 09:00:00
- Vault scanned: 4 pending, 2 approvals, 1 plan active
- Health: Busy 🟡 — attention needed
- Briefing saved: Briefing_2026-02-22.md
- Handed off to: AG03 Task Orchestrator
```

---
*Agent: Panaversity AI Employee — Silver Tier | AG05*
*First agent of every session — sets context for everything that follows.*
