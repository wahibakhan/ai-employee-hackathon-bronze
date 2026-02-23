---
type: agent
agent_id: AG01
name: Email Triage Agent
version: 1.0
tier: silver
trigger: "EMAIL_*.md appears in Needs_Action/"
skills_used: [SK01, SK02, SK03, SK05, SK06, SK07]
chains_to: [AG03, AG04]
created: 2026-02-22
---

# AG01 — Email Triage Agent

## Description
Processes incoming email task files created by the Gmail Watcher. Reads each
`EMAIL_*.md`, classifies urgency, decides the correct response path, and either
drafts a reply, escalates for approval, or archives — all with full audit trail.

This agent is the first responder for all email-originated tasks.

---

## Trigger Conditions

- Gmail Watcher creates a new `EMAIL_[id].md` in `Needs_Action/`
- User says: `Activate Agent: Email Triage Agent`
- User says: `Activate Agent: Email Triage Agent with file: EMAIL_18f3a.md`
- AG03 Task Orchestrator routes an email-type task here

---

## Skills Chain

```
SK01 Task Analyzer       → classify email, detect sensitivity
SK02 Plan Creator        → build response plan (if complex)
SK05 Email Drafter       → compose reply draft
SK03 Approval Requester  → gate if sensitive (payment/legal/contract)
SK06 File Mover & Logger → archive to Done/ when complete
SK07 Dashboard Updater   → log all actions
```

---

## Reasoning Loop (Iterate Until Complete)

```
LOOP START — for each EMAIL_*.md in Needs_Action/:

  ── ITERATION 1: UNDERSTAND ──────────────────────────────
  READ    EMAIL_[id].md
  EXTRACT sender, subject, snippet, priority, received_at
  CHECK   Is this email already processed? (status != pending) → SKIP

  ── ITERATION 2: CLASSIFY ────────────────────────────────
  CALL    SK01 Task Analyzer
  DECIDE  email_type from subject + snippet:
            "invoice"    → flag FINANCIAL, requires_approval = true
            "urgent"     → escalate priority to CRITICAL
            "meeting"    → create calendar note
            "complaint"  → flag HIGH priority, draft apology
            "newsletter" → flag LOW, archive directly
            "unknown"    → flag for human, do NOT proceed

  IF email_type == unknown:
      APPEND "⚠️ Unable to classify — human review needed"
      CALL   SK07 Dashboard Updater with action: unclassified email flagged
      STOP   this iteration — move to next file

  ── ITERATION 3: PLAN ────────────────────────────────────
  IF complexity == simple (single clear action):
      SKIP SK02 — proceed directly to drafting
  IF complexity == multi-step:
      CALL SK02 Plan Creator with objective: [email subject response]
      READ generated Plan_[slug].md before continuing

  ── ITERATION 4: DRAFT RESPONSE ──────────────────────────
  CALL    SK05 Email Drafter with context: [email summary + tone]
  OUTPUT  EMAIL_DRAFT_[sender-slug].md in Needs_Action/
  VERIFY  draft covers all points from original email

  ── ITERATION 5: SENSITIVITY GATE ────────────────────────
  IF requires_approval == true:
      CALL   SK03 Approval Requester with action: [describe sensitive action]
      CREATE APPROVAL_[slug].md
      SET    status: awaiting_approval
      CHAIN  → AG04 Approval Handler Agent
      PAUSE  — do not continue until approval received

  IF requires_approval == false:
      SET    EMAIL_[id].md status: triaged
      NOTIFY "Draft ready for human review: EMAIL_DRAFT_[slug].md"

  ── ITERATION 6: CLOSE ───────────────────────────────────
  CALL    SK07 Dashboard Updater with action: email triaged
  CALL    SK06 File Mover & Logger → move EMAIL_[id].md to Done/
  LOG     "AG01 Email Triage Agent: processed [filename] at [timestamp]"

LOOP END — check for next EMAIL_*.md
```

---

## Output Files Created

| File | Location | Purpose |
|------|----------|---------|
| `EMAIL_DRAFT_[slug].md` | Needs_Action/ | Reply draft for human review |
| `Plan_[slug].md` | Needs_Action/ | Multi-step plan (if complex) |
| `APPROVAL_[slug].md` | Needs_Action/ | Approval gate (if sensitive) |
| `EMAIL_[id].md` (updated) | Done/ | Archived with analysis appended |
| Dashboard.md.md (updated) | AI_Employee/ | Activity logged |

---

## Example Invocation

```
Activate Agent: Email Triage Agent
```
*Processes ALL pending EMAIL_*.md files in Needs_Action/*

```
Activate Agent: Email Triage Agent with file: EMAIL_18f3a2b4c.md
```
*Processes single specific email task*

```
Activate Agent: Email Triage Agent with filter: priority=high
```
*Processes only high-priority emails first*

---

## Sample Output — Dashboard Entry

```markdown
### AG01 Email Triage Agent — 2026-02-22 10:15:00
- Processed: EMAIL_18f3a2b.md (From: ahmed@client.com | Subject: Invoice Query)
- Classification: FINANCIAL → escalated to AG04
- Draft created: EMAIL_DRAFT_ahmed-invoice.md
- Approval requested: APPROVAL_invoice-reply-ahmed.md
- Status: Awaiting human approval
```

---
*Agent: Panaversity AI Employee — Silver Tier | AG01*
*Compliant with Company_Handbook — human approval required for all outbound actions*
