---
type: approval_request
action: instagram_dm
subject: "example_username"
status: pending
created: "2026-02-23"
requires_human_approval: true
---

# Approval Request — Instagram DM  *(TEMPLATE)*

**Action:** Send DM to @example_username

**Details:**
Message text goes here. Review carefully before approving.

---

## How to Approve

1. Rename this file:  `APPROVAL_INSTAGRAM_DM_<username>.md`
2. Change `status: pending` → `status: approved` in the YAML above.
3. Move file to: `AI_Employee/Approved/APPROVAL_INSTAGRAM_DM_<username>.md`
4. Re-run the `send_dm` MCP tool.

## How to Reject

Move this file to: `AI_Employee/Rejected/`

---
*Agent: Panaversity AI Employee — Silver Tier | Template*
