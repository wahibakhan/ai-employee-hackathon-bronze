#!/usr/bin/env python3
"""
gmail_watcher.py — Gmail Watcher (Silver Tier)
================================================
Panaversity Personal AI Employee Hackathon 0 — Silver Tier

Monitors Gmail for unread important emails and creates structured Obsidian
task files in the vault's Needs_Action/ folder — ready for the file watcher
(watcher.py) or a human to pick up and action.

Agent Skill Pattern:
    fetch_items()   → Gmail API → unread important message list
    process_item()  → write EMAIL_[id].md to Needs_Action/
    update_dashboard() → log activity to Dashboard.md.md  (inherited)

Usage:
    python gmail_watcher.py /mnt/c/projects/ai_employee/bronze

OAuth Credentials:
    Place credentials.json in vault root  OR  set GOOGLE_CREDENTIALS_PATH env var.
    Get it from: https://console.cloud.google.com/ → APIs & Services → Credentials
    (OAuth 2.0 Client ID → Desktop App → Download JSON)

First run opens a browser for Google OAuth consent.
token.json is saved automatically for subsequent runs.

Install dependencies:
    pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Dependency guard ──────────────────────────────────────────────────────────
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print(
        "\nERROR: Missing Google API packages.\n"
        "Install them with:\n\n"
        "  pip install google-api-python-client "
        "google-auth-oauthlib google-auth-httplib2\n"
    )
    sys.exit(1)

# ── Local import ──────────────────────────────────────────────────────────────
try:
    from base_watcher import BaseWatcher
except ImportError:
    print(
        "\nERROR: base_watcher.py not found.\n"
        "Ensure base_watcher.py is in the same directory as gmail_watcher.py.\n"
    )
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────

GMAIL_SCOPES    = ["https://www.googleapis.com/auth/gmail.readonly"]
GMAIL_QUERY     = "is:unread is:important"    # Gmail search query
MAX_RESULTS     = 25                          # Max emails fetched per poll
POLL_INTERVAL   = 120                         # Seconds between Gmail checks
AGENT_SIGNATURE = "Gmail Watcher — Panaversity AI Employee Hackathon Silver Tier"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)


# ── GmailWatcher ──────────────────────────────────────────────────────────────

class GmailWatcher(BaseWatcher):
    """
    Silver Tier Gmail Watcher.

    Extends BaseWatcher to monitor Gmail for unread important emails.
    Each new email becomes a structured .md task file in Needs_Action/.

    Task file naming:   EMAIL_[gmail_message_id].md
    YAML frontmatter:   type, from, subject, received, priority, status
    Body:               email snippet + suggested action checkboxes
    """

    def __init__(self, vault_path: str, interval: int = POLL_INTERVAL) -> None:
        super().__init__(vault_path=vault_path, interval=interval, name="GmailWatcher")
        self.service = self._authenticate()

    # ── OAuth Authentication ──────────────────────────────────────────────────

    def _resolve_credentials_path(self) -> Path:
        """
        Locate credentials.json in order of priority:
          1. GOOGLE_CREDENTIALS_PATH environment variable
          2. vault_path/credentials.json
          3. vault_path/AI_Employee/credentials.json
        """
        # Priority 1: explicit env var
        env_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "").strip()
        if env_path and Path(env_path).is_file():
            self.logger.info(f"Credentials → env var: {env_path}")
            return Path(env_path)

        # Priority 2: vault root
        root_creds = self.vault_path / "credentials.json"
        if root_creds.is_file():
            self.logger.info(f"Credentials → vault root: {root_creds}")
            return root_creds

        # Priority 3: AI_Employee subfolder
        sub_creds = self.vault_path / "AI_Employee" / "credentials.json"
        if sub_creds.is_file():
            self.logger.info(f"Credentials → AI_Employee/: {sub_creds}")
            return sub_creds

        raise FileNotFoundError(
            "\ncredentials.json not found. Steps to fix:\n"
            "  1. Go to https://console.cloud.google.com/\n"
            "  2. Create a project → Enable Gmail API\n"
            "  3. APIs & Services → Credentials → Create OAuth 2.0 Client ID (Desktop)\n"
            "  4. Download JSON → rename to credentials.json\n"
            f"  5. Place it at: {root_creds}\n"
            "  OR set env var: export GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json\n"
        )

    def _authenticate(self):
        """
        Run Google OAuth2 flow.

        - Loads saved token from token.json if valid.
        - Refreshes expired token automatically.
        - On first run: opens browser for consent, saves token.json.
        Returns an authenticated Gmail API service object.
        """
        creds      = None
        token_path = self.vault_path / "token.json"
        creds_path = self._resolve_credentials_path()

        # Load cached token
        if token_path.is_file():
            creds = Credentials.from_authorized_user_file(
                str(token_path), GMAIL_SCOPES
            )
            self.logger.info("Loaded cached OAuth token.")

        # Refresh or run full OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.logger.info("Token expired — refreshing…")
                try:
                    creds.refresh(Request())
                    self.logger.info("Token refreshed successfully.")
                except Exception as exc:
                    self.logger.warning(f"Token refresh failed ({exc}). Re-authenticating…")
                    creds = None

            if not creds:
                self.logger.info(
                    "Starting OAuth browser flow "
                    "(a browser window will open for Google sign-in)…"
                )
                flow  = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path), GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
                self.logger.info("OAuth consent granted.")

            # Persist token for future runs
            token_path.write_text(creds.to_json(), encoding="utf-8")
            self.logger.info(f"Token saved → {token_path}")

        service = build("gmail", "v1", credentials=creds)
        self.logger.info("Gmail API service ready.")
        return service

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _header(headers: list[dict], name: str) -> str:
        """Extract a named header value from a Gmail message payload."""
        for h in headers:
            if h.get("name", "").lower() == name.lower():
                return h.get("value", "").strip()
        return "Unknown"

    @staticmethod
    def _safe_filename_part(text: str, max_len: int = 40) -> str:
        """Strip characters unsafe for filenames, truncate to max_len."""
        safe = "".join(
            c if (c.isalnum() or c in " -_") else "_"
            for c in text
        )
        return safe.strip()[:max_len]

    # ── BaseWatcher interface ─────────────────────────────────────────────────

    def fetch_items(self) -> list:
        """
        Query Gmail for unread important messages.
        Filters out already-processed IDs.
        Returns list of full message metadata dicts.
        """
        try:
            response = (
                self.service.users()
                .messages()
                .list(userId="me", q=GMAIL_QUERY, maxResults=MAX_RESULTS)
                .execute()
            )
        except HttpError as exc:
            self.logger.error(f"Gmail list() failed: {exc}")
            return []

        raw_messages = response.get("messages", [])
        if not raw_messages:
            return []

        new_items: list[dict] = []
        for msg in raw_messages:
            msg_id = msg["id"]
            if msg_id in self._processed_ids:
                continue  # Already handled this session

            # Fetch metadata headers for this message
            try:
                full_msg = (
                    self.service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_id,
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"],
                    )
                    .execute()
                )
                new_items.append(full_msg)
            except HttpError as exc:
                self.logger.warning(f"Could not fetch message {msg_id}: {exc}")

        return new_items

    def process_item(self, message: dict) -> str | None:
        """
        Convert one Gmail message into a structured Obsidian task file.

        File:   Needs_Action/EMAIL_[message_id].md
        Returns filename on success, None on skip or error.
        """
        msg_id = message.get("id", "")

        # Guard: skip if already processed (safety net on top of fetch_items)
        if msg_id in self._processed_ids:
            self.logger.debug(f"Skipping already-processed ID: {msg_id}")
            return None

        # Extract headers and snippet
        headers  = message.get("payload", {}).get("headers", [])
        sender   = self._header(headers, "From")
        subject  = self._header(headers, "Subject")
        received = self._header(headers, "Date")
        snippet  = message.get("snippet", "").replace("\n", " ").strip()

        # Sanitize for display (strip stray quotes that break YAML)
        sender_safe  = sender.replace('"', "'")
        subject_safe = subject.replace('"', "'")

        filename = f"EMAIL_{msg_id}.md"
        filepath = self.needs_action / filename
        now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content = f"""\
---
type: email
status: pending
message_id: {msg_id}
from: "{sender_safe}"
subject: "{subject_safe}"
received: "{received}"
created: {now}
priority: high
source: gmail
---

## {subject}

| Field    | Value |
|----------|-------|
| **From** | {sender} |
| **Date** | {received} |
| **ID**   | `{msg_id}` |

---

### Preview

> {snippet if snippet else "_No preview available._"}

---

### Suggested Actions

- [ ] Open and read full email in Gmail
- [ ] Reply to sender
- [ ] Delegate to relevant team member
- [ ] Schedule follow-up task
- [ ] File / archive email
- [ ] Mark as done → move this file to Done/

---

*Created by {AGENT_SIGNATURE}*
*Processed at: {now}*
"""

        try:
            filepath.write_text(content, encoding="utf-8")
        except OSError as exc:
            self.logger.error(f"Could not write {filename}: {exc}")
            return None

        # Mark as processed only after successful write
        self._processed_ids.add(msg_id)
        self.logger.info(
            f"  CREATED  {filename}\n"
            f"           From   : {sender[:60]}\n"
            f"           Subject: {subject[:60]}"
        )
        return filename


# ── Entry Point ───────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print(
            "\nUsage:   python gmail_watcher.py <vault_path>\n"
            "Example: python gmail_watcher.py /mnt/c/projects/ai_employee/bronze\n"
        )
        sys.exit(1)

    vault_path = sys.argv[1]

    if not os.path.isdir(vault_path):
        print(f"\nERROR: Vault path does not exist: {vault_path}\n")
        sys.exit(1)

    watcher = GmailWatcher(vault_path=vault_path, interval=POLL_INTERVAL)
    watcher.watch()


if __name__ == "__main__":
    main()
