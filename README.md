# AI Employee Hackathon — Bronze & Silver Tier

**Panaversity Personal AI Employee Hackathon 0**

A local-first AI Employee powered by Claude, using an Obsidian vault as memory and dashboard.

---

## Project Structure

```
bronze/
├── watcher.py           # Silver Tier — autonomous file watcher (polling, WSL-safe)
├── start_watcher.sh     # One-click startup script
├── .gitignore           # Protects secrets and personal vault data
└── AI_Employee/         # Obsidian Vault (local memory)
    ├── Dashboard.md.md  # Live status dashboard
    ├── Company_Handbook.md.md  # AI Employee rules & principles
    ├── Needs_Action/    # Drop .md task files here (gitignored)
    └── Done/            # Processed tasks land here (gitignored)
```

---

## How It Works

### Bronze Tier — Manual Cycle
1. Drop a `.md` file with YAML frontmatter (`status: pending`) into `Needs_Action/`
2. Claude reads, processes, updates status → `processed`, moves to `Done/`
3. Dashboard is updated with activity log

### Silver Tier — Autonomous Watcher
```bash
python3 watcher.py
# or
./start_watcher.sh
```
- Polls `Needs_Action/` every 5 seconds
- Auto-processes any `status: pending` task
- Updates YAML frontmatter, appends processing note, moves to `Done/`
- Logs activity to `Dashboard.md.md`

---

## Task File Format

```markdown
---
type: task_type
status: pending
created: 2026-02-22
priority: high
---

Task description here.
```

---

## Setup

No external dependencies required — pure Python 3 stdlib.

```bash
git clone https://github.com/wahibakhan/ai-employee-hackathon-bronze.git
cd ai-employee-hackathon-bronze
python3 watcher.py
```

> **Note:** `Needs_Action/` and `Done/` folders are gitignored to protect personal task data. Create them locally after cloning.

---

## Security

- All data stays **local** in the Obsidian vault
- API keys and secrets are **never committed** (see `.gitignore`)
- Human approval required for any sensitive actions (per Company Handbook)

---

*Panaversity Personal AI Employee Hackathon 0 — Bronze/Silver Tier*
