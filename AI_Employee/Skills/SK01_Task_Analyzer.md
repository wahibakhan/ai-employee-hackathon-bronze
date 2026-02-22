---
type: agent_skill
skill_id: SK01
name: Task Analyzer
version: 1.0
tier: silver
trigger: "analyze task"
created: 2026-02-22
---

# SK01 — Task Analyzer

## Purpose
Read any task file from `Needs_Action/`, extract structured information, classify priority, detect type, and prepare a clean summary for downstream skills or human review.

---

## Trigger Conditions

- A new `.md` file appears in `Needs_Action/`
- User says: `Use Skill: Task Analyzer with file: [filename]`
- Gmail Watcher or File Watcher creates a new task
- Any skill needs to understand a task before acting

---

## Thinking Pattern (Step-by-Step)

```
STEP 1 — READ
  Read the target file from Needs_Action/
  Extract YAML frontmatter: type, from, subject, priority, status, created

STEP 2 — CLASSIFY
  Determine task type:
    - email      → requires reply, review, or delegation
    - invoice    → requires payment approval (SENSITIVE)
    - meeting    → requires scheduling
    - client     → requires relationship action
    - internal   → team/admin task
    - unknown    → flag for human review

STEP 3 — DETECT KEYWORDS
  Scan body for priority keywords (from Company_Handbook):
    URGENT / ASAP / invoice / payment / client / help / deadline
  If found → escalate priority to HIGH

STEP 4 — ASSESS SENSITIVITY
  Is action required: payment / deletion / sending real email / new contact?
  If YES → mark requires_approval: true
  If NO  → mark requires_approval: false

STEP 5 — PRODUCE ANALYSIS BLOCK
  Write structured analysis as output (see Output Format below)

STEP 6 — UPDATE YAML
  Update status: analyzed in the task file
  Add field: analyzed_at: [timestamp]
```

---

## Output Format

Append this block to the task file body:

```markdown
---
### 🔍 Task Analysis — [timestamp]

| Field          | Value |
|----------------|-------|
| **Type**       | email / invoice / meeting / internal |
| **Priority**   | HIGH / MEDIUM / LOW |
| **Sensitive**  | Yes / No |
| **Keywords**   | urgent, invoice, client (detected) |
| **Recommended Skill** | SK02 Plan Creator / SK03 Approval Requester |
| **Summary**    | One-sentence summary of what needs to happen |

**Suggested Next Step:** Use Skill: [next skill] with context: [brief context]
```

Also update YAML:
```yaml
status: analyzed
analyzed_at: 2026-02-22 10:00:00
requires_approval: false
recommended_skill: SK02
```

---

## Rules

- NEVER modify the original task content — only append
- If type is unknown, always recommend human review
- Payment/invoice tasks MUST trigger SK03 Approval Requester
- Log analysis to Dashboard via SK07

---

## Example Invocation

```
Use Skill: Task Analyzer with file: EMAIL_18f3a2b.md
```

```
Use Skill: Task Analyzer with file: BRONZE_PROOF_TEST.md
```

**Expected output:** Analysis block appended, YAML updated to `status: analyzed`

---
*Agent: Panaversity AI Employee — Silver Tier | SK01*
