#!/usr/bin/env python3
"""
inbox_watcher.py — Filesystem Inbox Watcher (Silver Tier)
==========================================================
Panaversity Personal AI Employee Hackathon 0 — Silver Tier

Monitors an Inbox/ folder inside the vault. When any file is dropped
into Inbox/, it is copied to Needs_Action/ and a metadata .md task file
is created — ready for the file watcher (watcher.py) to pick up.

Usage:
    python inbox_watcher.py /mnt/c/projects/ai_employee/bronze

Install:
    pip install watchdog
"""

import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Dependency guard ──────────────────────────────────────────────────────────
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers.polling import PollingObserver  # WSL-safe: no inotify
except ImportError:
    print(
        "\nERROR: watchdog is not installed.\n"
        "Fix it with:\n\n"
        "  pip install watchdog\n"
    )
    sys.exit(1)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("InboxWatcher")

AGENT_SIGNATURE = "Inbox Watcher — Panaversity AI Employee Hackathon Silver Tier"


# ── Event Handler ─────────────────────────────────────────────────────────────

class InboxHandler(FileSystemEventHandler):
    """
    Handles file creation events inside Inbox/.

    On each new file:
      1. Copy the file to Needs_Action/
      2. Create a FILE_DROP_[name].md metadata task file in Needs_Action/
    """

    def __init__(self, needs_action: Path) -> None:
        super().__init__()
        self.needs_action = needs_action

    def on_created(self, event) -> None:
        # Ignore directory creation events
        if event.is_directory:
            return

        src = Path(event.src_path)

        # Ignore hidden/temp files (e.g. .part, .tmp, .DS_Store)
        if src.name.startswith(".") or src.suffix in (".tmp", ".part", ".crdownload"):
            log.debug(f"Ignored temp file: {src.name}")
            return

        log.info(f"New file detected: {src.name}")
        self._handle_file(src)

    def _handle_file(self, src: Path) -> None:
        """Copy file to Needs_Action/ and write the metadata .md task file."""

        # Wait briefly for the file write to finish (avoids reading partial files)
        time.sleep(0.5)

        if not src.exists():
            log.warning(f"File disappeared before processing: {src.name}")
            return

        now     = datetime.now()
        ts_str  = now.strftime("%Y-%m-%d %H:%M:%S")
        size    = src.stat().st_size

        # ── Copy original file to Needs_Action/ ───────────────────────────────
        dest_file = self.needs_action / src.name
        try:
            shutil.copy2(src, dest_file)
            log.info(f"  Copied  → Needs_Action/{src.name}")
        except OSError as exc:
            log.error(f"  Could not copy {src.name}: {exc}")
            return

        # ── Write metadata .md task file ──────────────────────────────────────
        md_name = f"FILE_DROP_{src.name}.md"
        md_path = self.needs_action / md_name

        content = f"""\
---
type: file_drop
original_name: {src.name}
size: {size}
received: {ts_str}
status: pending
source: inbox_watcher
---

## New File Dropped: {src.name}

| Field             | Value |
|-------------------|-------|
| **File name**     | `{src.name}` |
| **Size**          | {size:,} bytes |
| **Received**      | {ts_str} |
| **Copied to**     | `Needs_Action/{src.name}` |

---

New file dropped into Inbox/ and queued for processing.

### Suggested Actions

- [ ] Review file contents
- [ ] Process / import into workflow
- [ ] Delete if not needed

---

*Created by {AGENT_SIGNATURE}*
*Logged at: {ts_str}*
"""

        try:
            md_path.write_text(content, encoding="utf-8")
            log.info(f"  Created → Needs_Action/{md_name}")
        except OSError as exc:
            log.error(f"  Could not write {md_name}: {exc}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print(
            "\nUsage:   python inbox_watcher.py <vault_path>\n"
            "Example: python inbox_watcher.py /mnt/c/projects/ai_employee/bronze\n"
        )
        sys.exit(1)

    vault_path = Path(sys.argv[1])

    if not vault_path.is_dir():
        print(f"\nERROR: Vault path does not exist: {vault_path}\n")
        sys.exit(1)

    # ── Set up directories ────────────────────────────────────────────────────
    inbox        = vault_path / "Inbox"
    needs_action = vault_path / "AI_Employee" / "Needs_Action"

    inbox.mkdir(parents=True, exist_ok=True)
    needs_action.mkdir(parents=True, exist_ok=True)

    # ── Start watchdog observer ───────────────────────────────────────────────
    handler  = InboxHandler(needs_action=needs_action)
    observer = PollingObserver(timeout=3)   # polls every 3s, works on /mnt/c/
    observer.schedule(handler, path=str(inbox), recursive=False)
    observer.start()

    log.info("=" * 60)
    log.info(f"  {AGENT_SIGNATURE}")
    log.info(f"  Watching : {inbox}")
    log.info(f"  Output   : {needs_action}")
    log.info("  Drop any file into Inbox/ to trigger processing.")
    log.info("  Press Ctrl+C to stop.")
    log.info("=" * 60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping watcher…")
        observer.stop()

    observer.join()
    log.info("Inbox Watcher stopped. Goodbye.")


if __name__ == "__main__":
    main()
