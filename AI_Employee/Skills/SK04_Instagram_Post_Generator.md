---
type: agent_skill
skill_id: SK04
name: Instagram Post Generator
version: 1.0
tier: silver
trigger: "write instagram"
created: 2026-02-23
---

# SK04 — Instagram Post Generator

## Purpose
Draft an engaging Instagram caption and hashtag set based on a topic, product, project, or announcement. Saves the draft as `Instagram_[slug].md` in `Needs_Action/` for human review before posting.

> **Rule:** Instagram posts are NEVER auto-published. Always routed through SK03 Approval Requester before any posting action.

---

## Trigger Conditions

- User says: `Use Skill: Instagram Post Generator with topic: [topic]`
- A task file contains `type: instagram_post`
- New product, project launch, or milestone needs to be announced
- Responding to a business DM that needs a public post follow-up

---

## Thinking Pattern (Step-by-Step)

```
STEP 1 — UNDERSTAND TOPIC
  What is the post about?
    - Product / service showcase?
    - Behind-the-scenes / process?
    - Achievement / milestone?
    - Announcement or offer?
  Who is the audience? (Clients / Followers / Buyers / Community)
  What format? (Feed post / Reel caption / Story text)

STEP 2 — READ CONTEXT
  Read Company_Handbook.md → brand voice and style rules
  Read Dashboard.md → recent activity for relevant context
  Check for source task file if provided (e.g. from Instagram DM watcher)

STEP 3 — DRAFT STRUCTURE
  Hook      → First line must stop the scroll (question, bold claim, emoji)
  Body      → 3-5 lines: story, value, or detail
  CTA       → Clear action (DM us, link in bio, comment below, save this)
  Hashtags  → 10-15 relevant hashtags (mix of niche + broad)
  Emojis    → Use sparingly, match brand tone

STEP 4 — TONE CHECK
  Visual and conversational — Instagram is personal, not corporate
  Short sentences, line breaks between each thought
  Avoid walls of text
  Match Company_Handbook communication style

STEP 5 — WRITE 2 VARIATIONS
  Version A — Story/emotion-driven (personal angle, relatable)
  Version B — Value/offer-driven (benefit-first, direct CTA)
  Human picks one or blends both

STEP 6 — SAVE DRAFT + ROUTE FOR APPROVAL
  Save to Needs_Action/Instagram_[slug].md
  Trigger SK03 Approval Requester before any posting
```

---

## Output Format

**File:** `Needs_Action/Instagram_[topic-slug].md`

```markdown
---
type: instagram_post
status: draft
topic: "[topic]"
format: feed_post
audience: "[target audience]"
created: [timestamp]
requires_approval: true
---

# Instagram Post Draft: [Topic]

---

## Version A — Story-Driven

[Hook — one punchy line or question]

[2-3 lines of story or context, one thought per line]

[Result or outcome]

[CTA — DM us / link in bio / comment below]

.
.
.
#hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5
#hashtag6 #hashtag7 #hashtag8 #AIEmployee #Panaversity

---

## Version B — Value-Driven

[Bold benefit or offer as hook]

[What you get / why it matters]

[Social proof or detail]

[Urgent or specific CTA]

.
.
.
#hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5
#hashtag6 #hashtag7 #hashtag8 #AIEmployee #Panaversity

---

## Posting Checklist
- [ ] Review both versions
- [ ] Choose Version A / B / Custom blend
- [ ] Add image/video description for designer
- [ ] Confirm hashtag relevance
- [ ] Run SK03 Approval Requester
- [ ] Post manually on Instagram
- [ ] Move this file to Done/
```

---

## Rules

- Draft ONLY — never post automatically
- Always include both versions (human chooses)
- No sensitive business details in public posts without explicit approval
- Tag accounts only if explicitly instructed
- Always route through SK03 before any publishing action
- Hashtags: mix 3-5 niche + 5-7 broad + 2-3 brand tags

---

## Example Invocations

```
Use Skill: Instagram Post Generator with topic: Launched AI Employee project at Panaversity Hackathon
```

```
Use Skill: Instagram Post Generator with topic: New design service package available
```

**Expected output:** `Instagram_launched-ai-employee-panaversity.md` in `Needs_Action/` with 2 draft versions + hashtag sets.

---
*Agent: Panaversity AI Employee — Silver Tier | SK04*
