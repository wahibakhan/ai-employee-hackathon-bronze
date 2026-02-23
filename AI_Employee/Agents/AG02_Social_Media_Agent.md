---
type: agent
agent_id: AG02
name: Social Media Agent
version: 1.0
tier: silver
trigger: "type: linkedin_post task or user call"
skills_used: [SK04, SK03, SK07]
chains_to: [AG04]
created: 2026-02-22
---

# AG02 — Social Media Agent

## Description
Creates professional LinkedIn content from project updates, milestones, or
explicit user requests. Always produces two draft versions, routes through
Approval Handler before any publishing action, and never auto-posts.

Focused on LinkedIn for Silver Tier. Expandable to Twitter/X, blog posts in
future tiers.

---

## Trigger Conditions

- User says: `Activate Agent: Social Media Agent with topic: [topic]`
- A task file in Needs_Action/ has `type: linkedin_post`
- AG03 Task Orchestrator detects a social/announcement task
- A Plan step calls for: "Announce [milestone] on LinkedIn"
- Scheduled content calendar entry (future: Gold Tier)

---

## Skills Chain

```
SK04 LinkedIn Post Generator → 2-version professional draft
SK03 Approval Requester      → human gate before any publishing
SK07 Dashboard Updater       → log draft creation and approval status
```

---

## Reasoning Loop (Iterate Until Complete)

```
LOOP START:

  ── ITERATION 1: GATHER CONTEXT ──────────────────────────
  READ   source task file (if triggered by file)
         OR accept topic/objective from user input
  READ   Company_Handbook.md → communication rules
  READ   Dashboard.md.md → recent activities for context
  READ   Done/ → last 3 completed tasks (for authentic content)

  IDENTIFY:
    topic        = what the post is about
    audience     = who will read it (clients / peers / recruiters)
    tone         = professional / celebratory / educational / thought-leadership
    hook_angle   = what makes this post worth stopping for?
    avoid        = confidential info / unannounced products / client names without permission

  ── ITERATION 2: CONTENT RESEARCH ────────────────────────
  THINK  What is genuinely valuable or interesting here?
  THINK  What would the audience learn, feel, or do after reading?
  THINK  What real detail (number, outcome, challenge overcome) adds credibility?
  THINK  What hashtags are relevant and not overused?

  IF topic is vague (less than 10 words of context):
      FLAG "Need more context for quality post"
      ASK  user: "What specific outcome or insight should be highlighted?"
      WAIT for response before proceeding

  ── ITERATION 3: DRAFT ───────────────────────────────────
  CALL   SK04 LinkedIn Post Generator with:
           topic:    [extracted topic]
           audience: [identified audience]
           tone:     [identified tone]
           context:  [relevant details from vault / user]

  VERIFY draft output contains:
    ✅ Hook line (first 1-2 lines grab attention)
    ✅ Story or insight (3-5 lines of substance)
    ✅ Takeaway or value (what reader gains)
    ✅ CTA (comment / connect / share / visit)
    ✅ 3-5 hashtags
    ✅ Two versions (A and B)
    ✅ No confidential data

  ── ITERATION 4: QUALITY GATE ────────────────────────────
  SELF-CHECK each version:
    - Does it sound human or robotic?
    - Is the hook strong enough to stop scrolling?
    - Is there one clear, specific idea (not everything at once)?
    - Is it under 1300 characters per version? (LinkedIn optimal)
    - Does it match Company_Handbook tone?

  IF quality low → rewrite weak sections before saving
  IF quality OK  → proceed

  ── ITERATION 5: APPROVAL GATE ───────────────────────────
  ALWAYS CALL SK03 Approval Requester for LinkedIn posts
  CREATE APPROVAL_linkedin-[slug].md with:
    - Both draft versions pasted inline
    - Audience and tone noted
    - Instructions: "Choose version, edit freely, then set status: approved"

  CHAIN → AG04 Approval Handler Agent
  PAUSE — Claude does NOT post — human posts manually after approval

  ── ITERATION 6: LOG & CLOSE ─────────────────────────────
  CALL   SK07 Dashboard Updater with action: LinkedIn draft created, awaiting approval
  UPDATE source task file status: drafted
  NOTE   "Post manually on LinkedIn after approval — Claude cannot auto-post"

LOOP END
```

---

## Output Files Created

| File | Location | Purpose |
|------|----------|---------|
| `LinkedIn_[slug].md` | Needs_Action/ | Draft post (2 versions) |
| `APPROVAL_linkedin-[slug].md` | Needs_Action/ | Approval gate |
| Dashboard.md.md (updated) | AI_Employee/ | Activity logged |

---

## Content Quality Standards

| Element | Standard |
|---------|----------|
| Hook | First line must work as a standalone statement |
| Length | 150–300 words per version (sweet spot for LinkedIn) |
| Tone | Professional but conversational — real person, not press release |
| Specificity | One concrete detail minimum (number, date, outcome) |
| CTA | Question or invitation — not "like and share" |
| Hashtags | 3-5 max — specific beats generic |

---

## Example Invocation

```
Activate Agent: Social Media Agent with topic: Just completed Bronze and Silver Tier of AI Employee Hackathon at Panaversity
```

```
Activate Agent: Social Media Agent with topic: Our Gmail Watcher now auto-creates Obsidian tasks from important emails
```

```
Activate Agent: Social Media Agent with file: Needs_Action/milestone_announcement.md
```

---

## Sample Output — Dashboard Entry

```markdown
### AG02 Social Media Agent — 2026-02-22 11:00:00
- Topic: AI Employee Hackathon milestone
- Draft: LinkedIn_ai-employee-hackathon.md (2 versions)
- Approval: APPROVAL_linkedin-hackathon.md created
- Status: Awaiting human approval and manual posting
```

---
*Agent: Panaversity AI Employee — Silver Tier | AG02*
*Rule: NEVER auto-post. Human reviews, edits, and posts manually.*
