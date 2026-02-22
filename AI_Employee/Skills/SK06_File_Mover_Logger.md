---
type: agent_skill
skill_id: SK06
name: File Mover & Logger
version: 1.0
tier: silver
trigger: "move file"
created: 2026-02-22
---

# SK06 — File Mover & Logger

## Purpose
Safely move task files between vault folders (`Needs_Action/` → `Done/`) and log every move with full audit trail. Ensures no file is lost or silently overwritten.

---

## Trigger Conditions

- Task is fully completed and ready to archive
- User says: `Use Skill: File Mover & Logger with file: [filename]`
- All checklist items in a task file are checked
- SK03 Approval Requester returns `status: rejected` (archive rejection)
- Watcher processes a file and needs to relocate it

---

## Thinking Pattern (Step-by-Step)

```
STEP 1 — READ SOURCE FILE
  Open the file from Needs_Action/
  Verify YAML status is: processed / approved / rejected / completed
  Check: are all action checkboxes done? (if applicable)
  If status still 'pending' → WARN and ask human to confirm

STEP 2 — DETERMINE DESTINATION
  Completed task   → Done/
  Rejected request → Done/ (with rejection note appended)
  Cancelled task   → Done/ (with cancellation reason)
  Archived email   → Done/

STEP 3 — PRE-MOVE CHECKS
  Does destination file already exist? (name conflict check)
  If conflict → rename: filename_[timestamp].md
  Confirm source file is readable and not empty

STEP 4 — APPEND MOVE LOG TO FILE
  Before moving, add audit block to end of file:
  "Moved by SK06 at [timestamp] | From: Needs_Action/ | To: Done/"

STEP 5 — EXECUTE MOVE
  Move file: Needs_Action/[filename] → Done/[filename]
  Verify file exists in Done/ after move
  Verify file is gone from Needs_Action/

STEP 6 — LOG TO DASHBOARD
  Call SK07 Dashboard Updater with:
    action: file_moved
    filename: [filename]
    from: Needs_Action/
    to: Done/
    timestamp: [now]
```

---

## Output Format

**Appended to file before move:**

```markdown
---
### 📦 Move Log — [timestamp]
- **Action:** Moved to Done/
- **From:** Needs_Action/[filename]
- **To:** Done/[filename]
- **Moved by:** SK06 File Mover & Logger
- **Final Status:** completed / rejected / archived
- **Note:** [optional reason or context]
```

**YAML updated before move:**
```yaml
status: completed
moved_at: 2026-02-22 10:30:00
moved_by: SK06
destination: Done/
```

**Dashboard entry (via SK07):**
```markdown
### SK06 File Move Log — [timestamp]
- Moved: `[filename]` → Done/
- Status: completed
```

---

## Conflict Resolution

| Scenario | Action |
|----------|--------|
| File already in Done/ | Rename with timestamp: `file_20260222_103000.md` |
| Source file empty | WARN — do not move, alert human |
| Source not found | Log error, alert human |
| Status still pending | WARN — confirm with human before moving |

---

## Rules

- NEVER delete files — only move
- ALWAYS append audit log before moving
- ALWAYS verify file arrived in Done/ after move
- Log every move to Dashboard (SK07)
- Name conflicts → timestamp suffix, never overwrite

---

## Example Invocation

```
Use Skill: File Mover & Logger with file: EMAIL_18f3a2b.md
```

```
Use Skill: File Mover & Logger with file: APPROVAL_send-payment-zara.md
```

```
Use Skill: File Mover & Logger with file: Plan_send-invoice-ahmed.md
```

**Expected output:** File moved to `Done/`, audit log appended, Dashboard updated.

---
*Agent: Panaversity AI Employee — Silver Tier | SK06*
