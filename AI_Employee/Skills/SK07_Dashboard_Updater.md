---
type: agent_skill
skill_id: SK07
name: Dashboard Updater
version: 1.0
tier: silver
trigger: "update dashboard"
created: 2026-02-22
---

# SK07 — Dashboard Updater

## Purpose
Keep `Dashboard.md.md` always current. Syncs task counts, logs activity, updates health status, and writes timestamped activity entries. Called by all other skills after any significant action.

---

## Trigger Conditions

- Any skill completes an action (called automatically)
- User says: `Use Skill: Dashboard Updater with action: [description]`
- Start of day / session → refresh counts
- File moved, task created, approval granted/rejected, email drafted

---

## Thinking Pattern (Step-by-Step)

```
STEP 1 — READ CURRENT DASHBOARD
  Open AI_Employee/Dashboard.md.md
  Note current values: pending tasks, last update, health status

STEP 2 — COUNT LIVE STATE
  Count .md files in Needs_Action/ → pending_count
  Count .md files in Done/         → done_count
  Check for APPROVAL_* files       → approvals_pending
  Check for Plan_* files           → plans_active

STEP 3 — DETERMINE HEALTH STATUS
  No tasks pending    → Idle / Monitoring
  1–3 tasks pending   → Active
  4+ tasks pending    → Busy
  APPROVAL pending    → Awaiting Human Input ⚠️
  Error logged        → Attention Required 🔴

STEP 4 — BUILD ACTIVITY ENTRY
  Compose timestamped log block for what just happened
  Include: skill used, action taken, file affected, outcome

STEP 5 — UPDATE DASHBOARD SECTIONS
  Update: Current Status block (counts, health, last update)
  Append: new activity entry to Recent Activity section
  Keep dashboard clean — only last 10 activity entries visible

STEP 6 — SAVE
  Write updated dashboard back
  Log: "Dashboard synced at [timestamp]"
```

---

## Output Format

**Updated `Current Status` section:**

```markdown
## Current Status
- Pending Tasks: [n]
- Active Plans: [n]
- Approvals Awaiting: [n]
- Completed Today: [n]
- Last Update: [timestamp]
- AI Employee Mode: Silver Tier — Active
- Overall Health: [Idle / Active / Busy / Awaiting Human Input]
```

**Appended activity entry:**

```markdown
### Activity Log — [timestamp]
- **Skill:** SK0X [Skill Name]
- **Action:** [What was done]
- **File:** `[filename]` (if applicable)
- **Outcome:** Success / Pending Approval / Error
- **Note:** [optional context]
```

---

## Dashboard Health Status Guide

| Condition | Status Label | Indicator |
|-----------|-------------|-----------|
| No pending tasks | Idle / Monitoring | ✅ |
| 1-3 tasks in queue | Active | 🔵 |
| 4+ tasks in queue | Busy | 🟡 |
| Approval file exists | Awaiting Human Input | ⚠️ |
| Error in last action | Attention Required | 🔴 |
| Watcher running | Monitoring | 👁️ |

---

## Rules

- Dashboard must be updated after EVERY skill execution
- Never delete existing activity entries — only append
- Keep `Current Status` block at the top — always accurate
- If dashboard file missing → create it with default template
- Trim to last 10 activity entries to prevent file bloat

---

## Example Invocation

```
Use Skill: Dashboard Updater with action: Task EMAIL_18f3a2b.md analyzed and moved to Done/
```

```
Use Skill: Dashboard Updater with action: Plan created for invoice to client Ahmed
```

```
Use Skill: Dashboard Updater with action: Session start — refreshing all counts
```

**Expected output:** Dashboard `Current Status` updated, new activity entry appended.

---

## Full Dashboard Template (if recreating from scratch)

```markdown
# AI Employee Dashboard

## Current Status
- Pending Tasks: 0
- Active Plans: 0
- Approvals Awaiting: 0
- Completed Today: 0
- Last Update: [timestamp]
- AI Employee Mode: Silver Tier — Active
- Overall Health: Idle / Monitoring ✅

## Recent Activity
[Activity entries appear here]

## Quick Links
- [[Company_Handbook]] → Rules and guidelines
- [[Skills/_SKILLS_INDEX]] → All agent skills
- Needs_Action/ → Incoming tasks
- Done/ → Completed tasks

*Panaversity Personal AI Employee Hackathon 0 — Silver Tier*
```

---
*Agent: Panaversity AI Employee — Silver Tier | SK07*
