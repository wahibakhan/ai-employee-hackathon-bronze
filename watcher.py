#!/usr/bin/env python3
"""
Silver Tier File Watcher - Panaversity Personal AI Employee Hackathon
======================================================================
Polls Needs_Action/ every POLL_INTERVAL seconds.
For each .md file with status: pending in YAML frontmatter:
  1. Updates status → processed + adds processed_at timestamp
  2. Appends a processing note to the file body
  3. Moves file to Done/
  4. Appends an activity entry to Dashboard.md.md

Pure stdlib — no external dependencies. WSL-safe (polling, no inotify).
"""

import os
import re
import shutil
import time
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
VAULT_ROOT      = "/mnt/c/projects/ai_employee/bronze/AI_Employee"
NEEDS_ACTION    = os.path.join(VAULT_ROOT, "Needs_Action")
DONE            = os.path.join(VAULT_ROOT, "Done")
DASHBOARD       = os.path.join(VAULT_ROOT, "Dashboard.md.md")
POLL_INTERVAL   = 5   # seconds between directory scans
AGENT_SIGNATURE = "Silver Tier Watcher — Panaversity AI Employee Hackathon"

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_frontmatter(content: str):
    """
    Split content into (frontmatter_dict, body_text).
    Returns (None, content) if no valid frontmatter block found.
    """
    match = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
    if not match:
        return None, content
    fm_lines = match.group(1).splitlines()
    fm = {}
    for line in fm_lines:
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    body = content[match.end():]
    return fm, body


def rebuild_frontmatter(fm: dict, body: str) -> str:
    """Reconstruct full file content from frontmatter dict + body."""
    lines = [f"{k}: {v}" for k, v in fm.items()]
    return "---\n" + "\n".join(lines) + "\n---\n" + body


# ── Core Agent Skill: Task Processor ─────────────────────────────────────────

def process_file(filepath: str, filename: str) -> bool:
    """
    Read, validate, update, and move a single task file.
    Returns True if file was processed, False if skipped.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        log(f"  ERROR reading {filename}: {e}")
        return False

    fm, body = parse_frontmatter(content)

    if fm is None:
        log(f"  SKIP  {filename} — no YAML frontmatter")
        return False

    status = fm.get("status", "").lower()
    if status != "pending":
        log(f"  SKIP  {filename} — status is '{status}' (expected 'pending')")
        return False

    log(f"  PROCESS  {filename}")

    # Update frontmatter
    ts = now_str()
    fm["status"] = "processed"
    fm["processed_at"] = ts

    # Append processing note to body
    note = (
        f"\n---\n"
        f"**Processed by {AGENT_SIGNATURE}**  \n"
        f"Timestamp: {ts}  \n"
        f"Action: status updated → processed, file moved to Done/\n"
    )
    updated_content = rebuild_frontmatter(fm, body + note)

    # Write changes back
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(updated_content)
    except OSError as e:
        log(f"  ERROR writing {filename}: {e}")
        return False

    # Move to Done/
    dest = os.path.join(DONE, filename)
    try:
        shutil.move(filepath, dest)
        log(f"  MOVED  {filename}  →  Done/")
    except OSError as e:
        log(f"  ERROR moving {filename}: {e}")
        return False

    return True


def update_dashboard(processed: list[str]) -> None:
    """Append a Silver Tier activity block to Dashboard.md.md."""
    if not processed:
        return
    ts = now_str()
    lines = [f"\n### Silver Tier Watcher Log — {ts}"]
    for name in processed:
        lines.append(f"- Processed & moved to Done/: `{name}`")
    lines.append(f"- Agent: {AGENT_SIGNATURE}")
    entry = "\n".join(lines) + "\n"
    try:
        with open(DASHBOARD, "a", encoding="utf-8") as f:
            f.write(entry)
        log(f"  DASHBOARD updated ({len(processed)} task(s) logged)")
    except OSError as e:
        log(f"  WARNING: could not update dashboard — {e}")


# ── Watcher Loop ──────────────────────────────────────────────────────────────

def watch() -> None:
    log("=" * 60)
    log(f"  {AGENT_SIGNATURE}")
    log(f"  Watching : {NEEDS_ACTION}")
    log(f"  Interval : {POLL_INTERVAL}s  |  Press Ctrl+C to stop")
    log("=" * 60)

    # Validate directories exist
    for d, label in [(NEEDS_ACTION, "Needs_Action"), (DONE, "Done")]:
        if not os.path.isdir(d):
            log(f"FATAL: {label} directory not found at {d}")
            return

    while True:
        try:
            candidates = [
                f for f in os.listdir(NEEDS_ACTION)
                if f.endswith(".md") and not f.startswith(".")
            ]

            if candidates:
                log(f"Scan: {len(candidates)} file(s) in Needs_Action/")
                processed = []
                for filename in sorted(candidates):
                    filepath = os.path.join(NEEDS_ACTION, filename)
                    if process_file(filepath, filename):
                        processed.append(filename)
                if processed:
                    update_dashboard(processed)
                else:
                    log("  No pending tasks found this scan.")

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log("\n=== Watcher stopped by user. Goodbye. ===")
            break
        except Exception as e:
            log(f"UNEXPECTED ERROR: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    watch()
