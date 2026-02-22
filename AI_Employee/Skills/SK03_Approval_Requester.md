---
type: agent_skill
skill_id: SK03
name: Approval Requester
version: 1.0
tier: silver
trigger: "request approval"
created: 2026-02-22
---

# SK03 — Approval Requester

## Purpose
Gate any sensitive or irreversible action behind explicit human approval. Creates a structured approval request file and PAUSES all further automation until human responds with APPROVED or REJECTED.

> **Core Principle (Company_Handbook):** Human is always in control.
> Never perform irreversible actions without approval.

---

## Trigger Conditions

- Task involves: payment, sending real email, deleting files, adding new contacts
- SK01 marks `requires_approval: true`
- SK02 Plan has a step marked `Sensitive: YES`
- User says: `Use Skill: Approval Requester with action: [describe action]`
- Any action with financial, legal, or relationship impact

---

## Sensitive Action Categories

| Category | Examples | Risk Level |
|----------|----------|------------|
| Financial | Pay invoice, transfer funds, purchase | CRITICAL |
| Communication | Send email, post on LinkedIn, message client | HIGH |
| Data | Delete file, overwrite record, export data | HIGH |
| Access | Add contact, grant permission, share document | MEDIUM |
| Scheduling | Book meeting, commit deadline, confirm appointment | MEDIUM |

---

## Thinking Pattern (Step-by-Step)

```
STEP 1 — IDENTIFY ACTION
  What exactly is the sensitive action?
  Who is affected? What is the impact if wrong?
  Is this reversible? (If not → CRITICAL priority)

STEP 2 — GATHER CONTEXT
  Read source task file
  Extract: what, who, when, why, consequences

STEP 3 — PRESENT OPTIONS
  Option A: APPROVE → Claude proceeds with action
  Option B: REJECT  → Claude stops, logs reason
  Option C: MODIFY  → Human edits details, then re-triggers

STEP 4 — CREATE APPROVAL FILE
  Write APPROVAL_[slug].md to Needs_Action/
  Set status: awaiting_approval
  HALT — do not proceed until file is updated by human

STEP 5 — WAIT FOR HUMAN RESPONSE
  Poll (or notify) for status change in APPROVAL file
  If status → approved:  proceed with action
  If status → rejected:  log and archive to Done/ with reason
  If status → modified:  re-read updated file, re-execute

STEP 6 — LOG OUTCOME
  Update Dashboard via SK07
  Move APPROVAL file to Done/
```

---

## Output Format

**File:** `Needs_Action/APPROVAL_[action-slug].md`

```markdown
---
type: approval_request
status: awaiting_approval
action: "[one-line description of action]"
risk_level: HIGH / CRITICAL / MEDIUM
reversible: false
source_task: "[source filename]"
created: [timestamp]
requested_by: Claude (AI Employee)
---

# ⚠️ Approval Required

## Action Requested
[Clear description of what Claude wants to do]

## Why This Needs Approval
[Risk explanation — what could go wrong if incorrect]

## Details

| Field | Value |
|-------|-------|
| **Action** | [Exact action] |
| **Target** | [File / person / system affected] |
| **Impact** | [What happens if approved] |
| **Reversible** | No / Yes |
| **Deadline** | [If time-sensitive] |

## Context
[Source task summary — why this action came up]

---

## ✅ To Approve
Edit this file and change status to `approved`:
```yaml
status: approved
approved_by: [your name]
approved_at: [timestamp]
```

## ❌ To Reject
```yaml
status: rejected
rejected_reason: [your reason]
```

## ✏️ To Modify
Update the details above and set:
```yaml
status: modified
```

---
*Created by SK03 Approval Requester — Panaversity AI Employee Silver Tier*
*⛔ Claude is PAUSED until this file status is updated.*
```

---

## Rules

- Claude MUST NOT proceed past this skill until `status: approved`
- APPROVAL files are NEVER auto-deleted — always moved to Done/
- All approvals are logged with timestamp and approver name
- If no response in 24h → create follow-up reminder task

---

## Example Invocation

```
Use Skill: Approval Requester with action: Send payment confirmation email to client Zara for PKR 50,000
```

```
Use Skill: Approval Requester with action: Delete duplicate contract file vendor_agreement_old.pdf
```

**Expected output:** `APPROVAL_send-payment-email-zara.md` in `Needs_Action/`, Claude paused.

---
*Agent: Panaversity AI Employee — Silver Tier | SK03*
