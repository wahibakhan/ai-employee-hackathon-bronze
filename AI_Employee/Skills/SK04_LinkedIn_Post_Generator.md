---
type: agent_skill
skill_id: SK04
name: LinkedIn Post Generator
version: 1.0
tier: silver
trigger: "write linkedin"
created: 2026-02-22
---

# SK04 — LinkedIn Post Generator

## Purpose
Draft a professional, engaging LinkedIn post based on a topic, achievement, or project update. Saves the draft as `LinkedIn_[slug].md` in `Needs_Action/` for human review before posting.

> **Rule:** LinkedIn posts are NEVER auto-published. Always routed through SK03 Approval Requester before any posting action.

---

## Trigger Conditions

- User says: `Use Skill: LinkedIn Post Generator with topic: [topic]`
- A task file contains type: linkedin_post
- Project milestone, launch, or achievement needs to be announced
- Weekly/monthly update cadence

---

## Thinking Pattern (Step-by-Step)

```
STEP 1 — UNDERSTAND TOPIC
  What is the post about?
    - Achievement / milestone?
    - Product / project launch?
    - Insight / lesson learned?
    - Personal update / announcement?
  Who is the audience? (Recruiters / Clients / Peers / General)

STEP 2 — READ CONTEXT
  Read Company_Handbook.md → communication style rules
  Read Dashboard.md → recent activity for relevant context
  Check for source task file if provided

STEP 3 — DRAFT STRUCTURE
  Hook    → 1-2 lines that stop the scroll
  Story   → 3-5 lines of substance (what happened, why it matters)
  Insight → Key takeaway or lesson (adds value)
  CTA     → Call to action (comment, connect, share, visit)
  Tags    → 3-5 relevant hashtags

STEP 4 — TONE CHECK
  Professional but human
  No jargon unless audience is technical
  Avoid: "I am pleased to announce" → Use real language
  Match Company_Handbook communication style: formal + respectful

STEP 5 — WRITE 2 VARIATIONS
  Version A — Story-driven (personal angle)
  Version B — Insight-driven (value-first angle)
  Human picks one or blends both

STEP 6 — SAVE DRAFT + ROUTE FOR APPROVAL
  Save to Needs_Action/LinkedIn_[slug].md
  Trigger SK03 Approval Requester before any posting
```

---

## Output Format

**File:** `Needs_Action/LinkedIn_[topic-slug].md`

```markdown
---
type: linkedin_post
status: draft
topic: "[topic]"
audience: "[target audience]"
created: [timestamp]
requires_approval: true
---

# LinkedIn Post Draft: [Topic]

---

## Version A — Story-Driven

[Hook line that grabs attention — short, bold idea]

[2-3 lines of story: what happened, the challenge, the moment]

[1-2 lines of outcome or result]

[Key insight or takeaway]

[CTA — question, invitation, or next step]

#Hashtag1 #Hashtag2 #Hashtag3 #AIEmployee #Panaversity

---

## Version B — Insight-Driven

[Bold insight or contrarian statement as hook]

[Evidence or example supporting the insight]

[Personal connection or experience]

[Broader implication for the reader]

[CTA]

#Hashtag1 #Hashtag2 #Hashtag3 #AIEmployee #Panaversity

---

## Posting Checklist
- [ ] Review both versions
- [ ] Choose Version A / B / Custom blend
- [ ] Add any personal details or specifics
- [ ] Run SK03 Approval Requester
- [ ] Post manually on LinkedIn
- [ ] Move this file to Done/

---
*Draft by SK04 LinkedIn Post Generator — Panaversity AI Employee Silver Tier*
```

---

## Rules

- Draft ONLY — never post automatically
- Always include both versions (human chooses)
- No sensitive business details in public posts without explicit approval
- Tag relevant people only if explicitly instructed
- Always route through SK03 before any publishing action

---

## Example Invocation

```
Use Skill: LinkedIn Post Generator with topic: Launched AI Employee project at Panaversity Hackathon
```

```
Use Skill: LinkedIn Post Generator with topic: Completed Bronze and Silver tier of personal AI agent
```

**Expected output:** `LinkedIn_launched-ai-employee-panaversity.md` in `Needs_Action/` with 2 draft versions.

---
*Agent: Panaversity AI Employee — Silver Tier | SK04*
