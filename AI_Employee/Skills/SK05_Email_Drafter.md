---
type: agent_skill
skill_id: SK05
name: Email Drafter
version: 1.0
tier: silver
trigger: "draft email"
created: 2026-02-22
---

# SK05 — Email Drafter

## Purpose
Compose a professional, context-aware email draft based on a task, instruction, or email thread. Saves draft as `EMAIL_DRAFT_[slug].md` in `Needs_Action/`. Never sends automatically — always requires human review + SK03 approval.

---

## Trigger Conditions

- User says: `Use Skill: Email Drafter with context: [context]`
- Task file has `type: email` and needs a reply
- SK02 Plan has a step: "Draft email to [recipient]"
- Incoming Gmail task requires response
- Any outbound communication needed

---

## Thinking Pattern (Step-by-Step)

```
STEP 1 — GATHER CONTEXT
  If replying to existing email:
    Read source EMAIL_[id].md from Needs_Action/
    Extract: sender, subject, original message snippet, tone
  If new email:
    Read instruction / task file for: recipient, purpose, key points

STEP 2 — READ COMPANY RULES
  Open Company_Handbook.md
  Apply: formal + respectful language
  Apply: clear next step at end of message
  Apply: no sensitive info without approval

STEP 3 — DETERMINE EMAIL TYPE
  Reply        → acknowledge + respond to all points
  Follow-up    → polite nudge, reference previous communication
  Introduction → warm, professional first contact
  Invoice      → formal, clear payment terms (SENSITIVE → SK03)
  Apology      → empathetic, solution-focused
  Update       → concise status report

STEP 4 — DRAFT EMAIL
  Subject line: clear, specific, not clickbait
  Opening: address recipient by name, reference context
  Body: cover all key points in short paragraphs
  Closing: clear next step / CTA
  Sign-off: professional (Regards / Best regards / Sincerely)

STEP 5 — SENSITIVITY CHECK
  Does email mention: payment, contract, legal, termination?
  If YES → add flag: requires_approval: true → trigger SK03
  If NO  → status: ready_for_review

STEP 6 — SAVE DRAFT
  Write to Needs_Action/EMAIL_DRAFT_[slug].md
  If sensitive → also create APPROVAL request via SK03
```

---

## Output Format

**File:** `Needs_Action/EMAIL_DRAFT_[recipient-slug].md`

```markdown
---
type: email_draft
status: draft
to: "[recipient email or name]"
subject: "[email subject line]"
reply_to_task: "[source task filename or None]"
created: [timestamp]
requires_approval: false
sensitive: false
---

# Email Draft: [Subject]

---

**To:** [Recipient Name] <email@domain.com>
**Subject:** [Subject Line]

---

Dear [Recipient Name],

[Opening — acknowledge context or reason for writing]

[Body paragraph 1 — main point or response]

[Body paragraph 2 — supporting detail, action, or question]

[Closing — clear next step]

Best regards,
[Your Name]
[Your Title]
[Contact Info]

---

## Draft Notes
- **Tone:** [Formal / Friendly / Apologetic / Assertive]
- **Key Points Covered:** [bullet list]
- **Missing Info Needed:** [anything human must fill in]
- **Sensitivity:** Low / High

## Send Checklist
- [ ] Review and personalise draft
- [ ] Fill in any [MISSING] placeholders
- [ ] Run SK03 Approval Requester (if sensitive)
- [ ] Send from your email client manually
- [ ] Move this file to Done/

---
*Draft by SK05 Email Drafter — Panaversity AI Employee Silver Tier*
```

---

## Rules

- NEVER send emails automatically — drafts only
- Always flag financial / legal content for SK03
- Always include "Missing Info Needed" section — don't guess unknowns
- Subject line must be specific — no "Following up" alone
- Match tone to relationship: client (formal), team (professional), vendor (clear)

---

## Example Invocation

```
Use Skill: Email Drafter with context: Reply to client Ahmed asking about project delay — be professional and give timeline update
```

```
Use Skill: Email Drafter with context: Send invoice follow-up to vendor who has not paid in 30 days
```

```
Use Skill: Email Drafter with context: Introduce myself to new contact Sarah from TechCorp after LinkedIn connection
```

**Expected output:** `EMAIL_DRAFT_ahmed-project-delay.md` in `Needs_Action/`, ready for human review.

---
*Agent: Panaversity AI Employee — Silver Tier | SK05*
