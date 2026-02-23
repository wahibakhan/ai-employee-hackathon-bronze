---
type: agents_index
version: 1.0
tier: silver
created: 2026-02-22
---

# Agents Index — Panaversity AI Employee (Silver Tier)

Agents are higher-order reasoning loops that chain multiple Skills together.
Skills do one thing. Agents decide *which* skills to call and *in what order*.

---

## Agent Registry

| # | Agent File | Trigger | Skills Used | Chains To |
|---|-----------|---------|-------------|-----------|
| 1 | [[AG01_Email_Triage_Agent]] | `EMAIL_*.md` in Needs_Action/ | SK01 SK02 SK03 SK05 SK06 SK07 | AG03 AG04 |
| 2 | [[AG02_Social_Media_Agent]] | `type: linkedin` task or user call | SK04 SK03 SK07 | AG04 |
| 3 | [[AG03_Task_Orchestrator_Agent]] | Any new file in Needs_Action/ | ALL skills | All agents |
| 4 | [[AG04_Approval_Handler_Agent]] | `APPROVAL_*.md` in Needs_Action/ | SK03 SK06 SK07 | AG03 |
| 5 | [[AG05_Daily_Briefing_Agent]] | Schedule / user call | SK07 + reads all folders | AG03 |

---

## Invocation Pattern

```
Activate Agent: [Agent Name]
Activate Agent: Email Triage Agent
Activate Agent: Task Orchestrator Agent with file: EMAIL_18f3a.md
Activate Agent: Daily Briefing Agent
Activate Agent: Approval Handler Agent with file: APPROVAL_payment-zara.md
```

---

## Agent vs Skill — When to use which

| Use a **Skill** when… | Use an **Agent** when… |
|-----------------------|------------------------|
| One specific action needed | Multiple decisions needed |
| You know exactly what to do | You need to figure out what to do |
| Called by an agent | Triggered by an event or user |
| Input/output is clear | Input varies, routing needed |

---

## Chaining Architecture

```
New file in Needs_Action/
        │
        ▼
AG03 Task Orchestrator          ← master router
        │
        ├─── EMAIL_*.md    ──▶  AG01 Email Triage Agent
        │                              │
        │                         SK01 → SK02 → SK05
        │                              │
        │                    [sensitive?] ──▶ AG04 Approval Handler
        │
        ├─── APPROVAL_*.md ──▶  AG04 Approval Handler Agent
        │
        ├─── linkedin task  ──▶  AG02 Social Media Agent
        │
        └─── morning call   ──▶  AG05 Daily Briefing Agent
                                       │
                                  SK07 → Dashboard update
```

---

## Human-in-the-Loop Gates

Every agent respects these hard stops:

1. **Payment / financial action** → STOP → AG04 Approval Handler
2. **Sending real email** → STOP → AG04 Approval Handler
3. **Deleting / overwriting files** → STOP → AG04 Approval Handler
4. **Publishing to social media** → STOP → AG04 Approval Handler
5. **Unknown task type** → STOP → flag for human, do not guess

---

*Panaversity Personal AI Employee Hackathon 0 — Silver Tier*
