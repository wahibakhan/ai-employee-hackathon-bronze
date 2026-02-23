---
type: skills_index
version: 1.0
tier: silver
created: 2026-02-22
---

# Agent Skills Index — Panaversity AI Employee (Silver Tier)

All skills live in `AI_Employee/Skills/`. Call any skill using the pattern:

```
Use Skill: [Skill Name] with [parameter]: [value]
```

---

## Available Skills

| # | Skill File | Trigger Keyword | Purpose |
|---|-----------|-----------------|---------|
| 1 | [[SK01_Task_Analyzer]] | `analyze task` | Read & classify any task file |
| 2 | [[SK02_Plan_Creator]] | `create plan` | Build structured action plan |
| 3 | [[SK03_Approval_Requester]] | `request approval` | Flag sensitive actions for human |
| 4 | [[SK04_Instagram_Post_Generator]] | `write instagram` | Draft Instagram captions + hashtags |
| 5 | [[SK05_Email_Drafter]] | `draft email` | Compose professional emails |
| 6 | [[SK06_File_Mover_Logger]] | `move file` | Move files + log all actions |
| 7 | [[SK07_Dashboard_Updater]] | `update dashboard` | Sync Dashboard.md status |

---

## Invocation Pattern

```
Use Skill: Plan Creator with objective: Send invoice to client Ahmed
Use Skill: Email Drafter with context: Follow up on Q1 proposal
Use Skill: Approval Requester with action: Delete vendor contract file
Use Skill: Instagram Post Generator with topic: Launched AI Employee project
```

---

## Skill Execution Rules (from Company_Handbook)

1. Always read source task file before acting
2. Never perform irreversible actions without Approval Requester skill
3. Log every action to Dashboard.md
4. Human is always final approver for: payments, emails sent, deletions
5. Skills chain — output of one skill can feed the next

---

## Skill Chaining Example

```
Email received (Gmail Watcher)
    → Use Skill: Task Analyzer        → classifies priority
    → Use Skill: Plan Creator         → builds action steps
    → Use Skill: Approval Requester   → if sensitive
    → Use Skill: Email Drafter        → drafts reply
    → Use Skill: Dashboard Updater    → logs completion
    → Use Skill: File Mover & Logger  → moves to Done/
```

---
*Panaversity Personal AI Employee Hackathon 0 — Silver Tier*
