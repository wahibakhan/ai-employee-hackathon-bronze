---
type: agent_skill
skill_id: SK02
name: Plan Creator
version: 1.0
tier: silver
trigger: "create plan"
created: 2026-02-22
---

# SK02 — Plan Creator

## Purpose
Take an objective or analyzed task and generate a clear, step-by-step action plan. Saves the plan as `Plan_[slug].md` in `Needs_Action/` and links it to the source task.

---

## Trigger Conditions

- SK01 Task Analyzer recommends Plan Creator
- User says: `Use Skill: Plan Creator with objective: [objective text]`
- A task has `status: analyzed` and no plan exists yet
- Complex task with multiple steps detected

---

## Thinking Pattern (Step-by-Step)

```
STEP 1 — READ CONTEXT
  Read source task file (if provided)
  Read Company_Handbook.md for relevant rules
  Extract: objective, constraints, deadline, stakeholders

STEP 2 — BREAK DOWN
  Decompose objective into atomic action steps
  Each step must be:
    - Specific and actionable
    - Assigned an owner (human / AI)
    - Marked as sensitive or not
    - Given a suggested skill (if AI-executable)

STEP 3 — ORDER STEPS
  Arrange steps in logical sequence
  Flag any steps that require approval before proceeding (SK03)
  Flag any steps that require external tools (email, file, etc.)

STEP 4 — ESTIMATE
  For each step: Simple / Medium / Complex
  Flag blockers: "Waiting for X before Y can proceed"

STEP 5 — WRITE PLAN FILE
  Create Plan_[slug].md in Needs_Action/
  Full YAML frontmatter + structured body

STEP 6 — LINK BACK
  In source task file, append:
  "Plan created: [[Plan_[slug]]]"
  Update source task status: planned
```

---

## Output Format

**File:** `Needs_Action/Plan_[objective-slug].md`

```markdown
---
type: plan
status: pending
objective: "[objective text]"
source_task: "[source filename or None]"
created: [timestamp]
priority: high
owner: human
---

# Plan: [Objective]

## Objective
[Clear one-sentence statement of what must be achieved]

## Context
[Why this plan exists — source task summary]

## Action Steps

### Step 1 — [Action Title]
- **Owner:** Human / Claude
- **Skill:** SK05 Email Drafter (if applicable)
- **Sensitive:** No
- **Details:** [What exactly to do]
- [ ] Done

### Step 2 — [Action Title]
- **Owner:** Human
- **Skill:** SK03 Approval Requester
- **Sensitive:** YES — requires human approval
- **Details:** [What exactly to do]
- [ ] Approved
- [ ] Done

### Step 3 — [Action Title]
- **Owner:** Claude
- **Skill:** SK07 Dashboard Updater
- **Sensitive:** No
- **Details:** Log completion to Dashboard
- [ ] Done

## Blockers
- None / [list any blockers]

## Success Criteria
- [ ] [What does "done" look like?]

---
*Created by SK02 Plan Creator — Panaversity AI Employee Silver Tier*
*Source: [[source_task_filename]]*
```

---

## Rules

- Every plan MUST have at least one success criterion
- Steps involving payments, emails, or deletions MUST include SK03
- Plan files are NOT moved to Done/ until ALL steps are checked
- Human owns final sign-off on all plans

---

## Example Invocation

```
Use Skill: Plan Creator with objective: Send invoice to client Ahmed for March services
```

```
Use Skill: Plan Creator with objective: Reply to urgent client email about project delay
```

**Expected output:** `Plan_send-invoice-client-ahmed.md` created in `Needs_Action/`

---
*Agent: Panaversity AI Employee — Silver Tier | SK02*
