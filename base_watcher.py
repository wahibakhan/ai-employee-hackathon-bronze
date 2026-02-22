#!/usr/bin/env python3
"""
base_watcher.py — Abstract Base Watcher
========================================
Panaversity Personal AI Employee Hackathon 0 — Silver Tier

Defines the BaseWatcher ABC that all AI Employee watchers must extend.
Implements the Agent Skill pattern:

    fetch_items()  →  process_item()  →  update_dashboard()

Each concrete watcher (FileSystemWatcher, GmailWatcher, etc.) only needs
to implement fetch_items() and process_item(). The watch loop, dashboard
updates, vault validation, and processed-ID deduplication are handled here.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

# ── Shared signature appended to every dashboard log entry ────────────────────
AGENT_SIGNATURE = "Panaversity AI Employee — Silver Tier"


# ── BaseWatcher ───────────────────────────────────────────────────────────────

class BaseWatcher(ABC):
    """
    Abstract base class for all AI Employee watchers.

    Subclasses must implement:
        fetch_items()   → list of raw items (emails, files, etc.)
        process_item()  → create a task .md file, return filename or None

    Attributes:
        vault_path      : pathlib.Path — root of the project (e.g. bronze/)
        interval        : int          — seconds between polls
        name            : str          — watcher name used in logs / dashboard
        needs_action    : Path         — Needs_Action/ directory
        done            : Path         — Done/ directory
        dashboard       : Path         — Dashboard.md.md file
        _processed_ids  : set          — IDs already handled (deduplication)
    """

    def __init__(
        self,
        vault_path: str,
        interval: int = 60,
        name: str = "BaseWatcher",
    ) -> None:
        self.vault_path = Path(vault_path)
        self.interval   = interval
        self.name       = name
        self.logger     = logging.getLogger(name)

        # Deduplication — persists for the lifetime of the process
        self._processed_ids: set[str] = set()

        # Standard vault paths
        vault_root       = self.vault_path / "AI_Employee"
        self.needs_action = vault_root / "Needs_Action"
        self.done         = vault_root / "Done"
        self.dashboard    = vault_root / "Dashboard.md.md"

        self._validate_vault()

    # ── Vault validation ──────────────────────────────────────────────────────

    def _validate_vault(self) -> None:
        """Create required vault directories if they don't exist."""
        for directory in (self.needs_action, self.done):
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Vault directory OK: {directory}")

        if not self.dashboard.exists():
            self.logger.warning(
                f"Dashboard not found at {self.dashboard}. "
                "It will be created on first update."
            )

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def fetch_items(self) -> list:
        """
        Fetch new items to process (emails, files, API events, etc.).
        Must return a list; return [] if nothing new.
        Subclasses are responsible for filtering already-processed items
        using self._processed_ids before returning.
        """

    @abstractmethod
    def process_item(self, item) -> str | None:
        """
        Process one item: create a task .md file in self.needs_action/.
        Returns the filename (str) on success, None if skipped/failed.
        Should add item ID to self._processed_ids when successful.
        """

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def update_dashboard(self, created_files: list[str], source: str = "") -> None:
        """
        Append a structured activity block to Dashboard.md.md.
        Safe to call with an empty list (no-op).
        """
        if not created_files:
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [f"\n### {self.name} Log — {ts}"]
        if source:
            lines.append(f"- Source: {source}")
        for fname in created_files:
            lines.append(f"- Task created: `{fname}`")
        lines.append(f"- Agent: {AGENT_SIGNATURE}")
        entry = "\n".join(lines) + "\n"

        try:
            with open(self.dashboard, "a", encoding="utf-8") as fh:
                fh.write(entry)
            self.logger.info(
                f"Dashboard updated — {len(created_files)} new task(s) logged."
            )
        except OSError as exc:
            self.logger.warning(f"Could not update dashboard: {exc}")

    # ── Main watch loop ───────────────────────────────────────────────────────

    def watch(self) -> None:
        """
        Blocking watch loop. Runs until KeyboardInterrupt (Ctrl+C).

        Cycle:
            1. fetch_items()          — get new raw items
            2. process_item(item)     — create task file for each
            3. update_dashboard(...)  — log activity to vault dashboard
            4. sleep(self.interval)
        """
        self.logger.info("=" * 62)
        self.logger.info(f"  {self.name}")
        self.logger.info(f"  Vault    : {self.vault_path}")
        self.logger.info(f"  Interval : {self.interval}s  |  Ctrl+C to stop")
        self.logger.info("=" * 62)

        while True:
            try:
                self.logger.info("Polling for new items…")
                items = self.fetch_items()

                if items:
                    self.logger.info(f"Found {len(items)} new item(s) to process.")
                    created: list[str] = []
                    for item in items:
                        fname = self.process_item(item)
                        if fname:
                            created.append(fname)
                    if created:
                        self.update_dashboard(created, source=self.name)
                    else:
                        self.logger.info("All items skipped (already processed or errors).")
                else:
                    self.logger.info("No new items found this cycle.")

                time.sleep(self.interval)

            except KeyboardInterrupt:
                self.logger.info("Watch loop stopped by user. Goodbye.")
                break
            except Exception as exc:          # noqa: BLE001 — keep watcher alive
                self.logger.error(f"Unexpected error in watch loop: {exc}", exc_info=True)
                self.logger.info(f"Retrying in {self.interval}s…")
                time.sleep(self.interval)
