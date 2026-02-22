#!/usr/bin/env python3
"""
whatsapp_watcher.py — WhatsApp Web Watcher (Silver Tier)
=========================================================
Panaversity Personal AI Employee Hackathon 0 — Silver Tier

Monitors WhatsApp Web for unread messages or messages containing
business-critical keywords. Converts matching messages into structured
Obsidian task files in the vault's Needs_Action/ folder — ready for the
file watcher (watcher.py) or a human to pick up and action.

Agent Skill Pattern (extends BaseWatcher):
    fetch_items()      → Playwright → WhatsApp Web DOM → keyword/unread chats
    process_item()     → write WHATSAPP_[sender]_[ts].md to Needs_Action/
    update_dashboard() → log activity to Dashboard.md.md  (inherited)

Session Persistence:
    Session data is stored in whatsapp_session/ (Chromium user-data-dir).
    First run  → headless=False  — browser window opens for QR scan.
    Subsequent → headless=True   — session restored silently from disk.

Usage:
    python whatsapp_watcher.py /mnt/c/projects/ai_employee/bronze

    # Force re-authentication (clear saved session):
    python whatsapp_watcher.py /mnt/c/projects/ai_employee/bronze --reset-session

Install:
    pip install playwright
    playwright install chromium

First run:
    A browser window will open. Open WhatsApp on your phone:
    Settings → Linked Devices → Link a Device → Scan QR code.

WSL Note:
    headless=False requires a display server.
    Windows 11 / WSLg: works out of the box.
    Windows 10      : install VcXsrv and set DISPLAY=:0 before running.
"""

import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Dependency guard ──────────────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import TimeoutError as PWTimeoutError
except ImportError:
    print(
        "\nERROR: Playwright is not installed.\n"
        "Fix it with:\n\n"
        "  pip install playwright\n"
        "  playwright install chromium\n"
    )
    sys.exit(1)

# ── Local import ──────────────────────────────────────────────────────────────
try:
    from base_watcher import BaseWatcher
except ImportError:
    print(
        "\nERROR: base_watcher.py not found.\n"
        "Ensure base_watcher.py is in the same directory as whatsapp_watcher.py.\n"
    )
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────

# Business-critical keywords to watch for (case-insensitive)
KEYWORDS: list[str] = [
    "price", "quote", "design", "urgent", "invoice",
    "payment", "help", "asap",
]

# High-urgency keywords that set priority: high on the task file
URGENT_KEYWORDS: set[str] = {"urgent", "asap", "help"}

POLL_INTERVAL      = 30       # seconds between WhatsApp Web polls
QR_TIMEOUT         = 180      # seconds to wait for phone QR scan
CHAT_LOAD_TIMEOUT  = 45_000   # ms — max wait for chat list after page load
PAGE_SETTLE_MS     = 3_000    # ms — brief wait after navigation for SPA to render
SESSION_MARKER     = "wa_session_ok"   # marker file inside whatsapp_session/
WHATSAPP_URL       = "https://web.whatsapp.com"
AGENT_SIGNATURE    = "WhatsApp Watcher — Panaversity AI Employee Hackathon Silver Tier"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ── JavaScript: extract unread/keyword chats from WhatsApp Web DOM ─────────────
#
# WhatsApp Web is a React SPA. Its exact class names change with updates, so
# we try multiple selector strategies in order and stop at the first that works.
# The returned list contains one dict per matching chat.
#
_JS_EXTRACT_CHATS = """
(keywords) => {
    const results  = [];
    const seenSend = new Set();

    // ── Strategy 1: official data-testid attributes ──────────────────────────
    // WhatsApp has used these consistently for several years.
    let chatItems = [...document.querySelectorAll(
        '[data-testid="cell-frame-container"]'
    )];

    // ── Strategy 2: ARIA role fallback ────────────────────────────────────────
    if (!chatItems.length) {
        chatItems = [...document.querySelectorAll('div[role="listitem"]')];
    }

    // ── Strategy 3: pane-side children (last resort) ──────────────────────────
    if (!chatItems.length) {
        const pane = document.querySelector('#pane-side');
        if (pane) {
            chatItems = [...pane.querySelectorAll('div[tabindex="-1"]')];
        }
    }

    for (const item of chatItems) {
        // ── Sender name (try several attribute/element combinations) ──────────
        const titleEl =
            item.querySelector('[data-testid="cell-frame-title"] span') ||
            item.querySelector('span[title]')                           ||
            item.querySelector('[data-testid="cell-frame-title"]');

        const sender = (
            titleEl?.getAttribute('title') ||
            titleEl?.textContent           ||
            ''
        ).trim();

        if (!sender || seenSend.has(sender)) continue;

        // ── Message preview ───────────────────────────────────────────────────
        const previewEl =
            item.querySelector('[data-testid="last-msg-preview"]')              ||
            item.querySelector('span.last-message-text')                        ||
            item.querySelector('[data-testid="cell-frame-secondary-detail"] span');

        const preview = (previewEl?.textContent || '').trim();

        // ── Unread indicator (green badge with count) ─────────────────────────
        const unreadEl =
            item.querySelector('[data-testid="icon-unread-count"]') ||
            item.querySelector('span[aria-label*="unread"]')        ||
            item.querySelector('span.unread-count');

        // Some builds mark the entire row with an "unread" CSS class
        const unreadByClass =
            item.className.includes('unread') ||
            !!item.querySelector('[class*="unread"]');

        const hasUnread    = !!unreadEl || unreadByClass;
        const unreadCount  = (unreadEl?.textContent || '').trim();

        // ── Keyword matching in the preview text ──────────────────────────────
        const lowerPrev = preview.toLowerCase();
        const matched   = keywords.find(kw => lowerPrev.includes(kw.toLowerCase()));

        if (hasUnread || matched) {
            seenSend.add(sender);
            results.push({
                sender:         sender,
                message:        preview,
                hasUnread:      hasUnread,
                unreadCount:    unreadCount || (hasUnread ? '1+' : '0'),
                matchedKeyword: matched || null,
            });
        }
    }

    return results;
}
"""

# ── WhatsAppWatcher ────────────────────────────────────────────────────────────

class WhatsAppWatcher(BaseWatcher):
    """
    Silver Tier WhatsApp Web Watcher.

    Extends BaseWatcher to monitor WhatsApp Web for unread messages and
    keyword-matched message previews.

    Session flow:
        1. If whatsapp_session/wa_session_ok exists → headless=True, resume.
        2. Otherwise → headless=False, open browser, wait for QR scan,
           then create the marker file to indicate a valid session.

    Task file naming:   WHATSAPP_[sender]_[YYYYmmdd_HHMMSS].md
    YAML frontmatter:   type, from, message, time, priority, status, trigger
    Body:               message preview + suggested action checkboxes
    """

    def __init__(self, vault_path: str, interval: int = POLL_INTERVAL) -> None:
        super().__init__(vault_path=vault_path, interval=interval, name="WhatsAppWatcher")

        # ── Session directory (Playwright persistent-context user-data-dir) ────
        self.session_dir    = Path(vault_path) / "whatsapp_session"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_marker = self.session_dir / SESSION_MARKER

        # ── Playwright objects (set up by _start_browser) ─────────────────────
        self._playwright       = None
        self._browser_context  = None
        self._page             = None

        # ── Launch browser and navigate to WhatsApp Web ───────────────────────
        self._start_browser()

    # ── Session helpers ────────────────────────────────────────────────────────

    def _session_exists(self) -> bool:
        """Return True if a previously saved session marker exists."""
        return self.session_marker.exists()

    def _mark_session(self) -> None:
        """Write the session marker file after a successful QR scan/login."""
        self.session_marker.touch()
        self.logger.info(f"Session marker saved: {self.session_marker}")

    def _clear_session(self) -> None:
        """Remove the session marker (forces QR re-scan on next start)."""
        self.session_marker.unlink(missing_ok=True)
        self.logger.info("Session marker cleared — next start will require QR scan.")

    # ── Browser lifecycle ──────────────────────────────────────────────────────

    def _start_browser(self) -> None:
        """
        Launch a Playwright persistent Chromium context.

        headless=False on first run (no session) → user scans QR.
        headless=True  on subsequent runs        → session restored silently.
        """
        headless = self._session_exists()
        mode     = "headless" if headless else "headed  (QR scan required)"
        self.logger.info(f"Browser mode : {mode}")
        self.logger.info(f"Session dir  : {self.session_dir}")

        self._playwright = sync_playwright().start()

        try:
            self._browser_context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-blink-features=AutomationControlled",
                ],
                viewport={"width": 1280, "height": 800},
                # Realistic user-agent to avoid WhatsApp's bot detection
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
        except Exception as exc:
            err = str(exc)
            if "display" in err.lower() or "DISPLAY" in err:
                self.logger.error(
                    "Cannot open browser window — no display detected.\n"
                    "On Windows 11 (WSLg): should work automatically.\n"
                    "On Windows 10 (WSL2): install VcXsrv, then:\n"
                    "  export DISPLAY=:0\n"
                    "  python whatsapp_watcher.py <vault_path>"
                )
            else:
                self.logger.error(f"Browser launch failed: {exc}")
            self._playwright.stop()
            raise

        # Reuse existing page or open a new one
        pages      = self._browser_context.pages
        self._page = pages[0] if pages else self._browser_context.new_page()

        # ── Navigate to WhatsApp Web ───────────────────────────────────────────
        self.logger.info(f"Navigating to {WHATSAPP_URL} …")
        try:
            self._page.goto(WHATSAPP_URL, timeout=30_000, wait_until="domcontentloaded")
        except Exception as exc:
            self.logger.error(f"Navigation failed: {exc}")
            self.close()
            raise

        # Brief pause for the React SPA to render initial state
        self._page.wait_for_timeout(PAGE_SETTLE_MS)

        if not headless:
            self._handle_qr_scan()
        else:
            self._verify_session()

    def _handle_qr_scan(self) -> None:
        """
        Wait for the user to scan the QR code with their phone.
        Blocks until the chat list is visible or QR_TIMEOUT is reached.
        """
        self.logger.info("=" * 62)
        self.logger.info("  ACTION REQUIRED — Open WhatsApp on your phone:")
        self.logger.info("  Settings → Linked Devices → Link a Device → Scan QR")
        self.logger.info(f"  Waiting up to {QR_TIMEOUT} seconds for scan…")
        self.logger.info("=" * 62)

        # Confirm QR code appeared in the browser
        try:
            self._page.wait_for_selector(
                '[data-testid="qrcode"], canvas[aria-label*="QR"], div[data-ref]',
                timeout=15_000,
            )
            self.logger.info("QR code visible — waiting for phone scan…")
        except PWTimeoutError:
            self.logger.info("QR element not detected; may already be partially loaded.")

        # Wait for the chat list — that means login was successful
        try:
            self._page.wait_for_selector(
                '[data-testid="chat-list"], #pane-side, [aria-label="Chat list"]',
                timeout=QR_TIMEOUT * 1_000,
            )
        except PWTimeoutError:
            raise RuntimeError(
                f"QR scan timed out after {QR_TIMEOUT}s. "
                "Please restart and scan the QR code promptly."
            )

        self.logger.info("QR scan successful — chat list loaded.")
        self._mark_session()

    def _verify_session(self) -> None:
        """
        Confirm the saved session is still valid after launching in headless mode.
        If WhatsApp shows the QR page, the session has expired — clear the marker.
        """
        self.logger.info("Verifying saved session…")
        try:
            self._page.wait_for_selector(
                '[data-testid="chat-list"], #pane-side, [aria-label="Chat list"]',
                timeout=CHAT_LOAD_TIMEOUT,
            )
            self.logger.info("Session valid — chat list loaded successfully.")
        except PWTimeoutError:
            # Check whether the QR code is now showing (session truly expired)
            qr_visible = self._page.locator(
                '[data-testid="qrcode"], canvas[aria-label*="QR"], div[data-ref]'
            ).is_visible()

            if qr_visible:
                self._clear_session()
                raise RuntimeError(
                    "WhatsApp session has expired (QR code visible).\n"
                    "Session marker removed. Restart to re-authenticate:\n"
                    "  python whatsapp_watcher.py <vault_path>"
                )
            else:
                # Possibly still loading — log a warning but continue
                self.logger.warning(
                    "Chat list not detected within timeout — WhatsApp may be slow. "
                    "Will attempt to poll anyway."
                )

    def _page_is_healthy(self) -> bool:
        """
        Quick sanity check: are we still on WhatsApp Web with a loaded page?
        Returns False if the page crashed, navigated away, or closed.
        """
        try:
            url = self._page.url
            return WHATSAPP_URL.rstrip("/") in url
        except Exception:
            return False

    def _reconnect(self) -> None:
        """
        Re-navigate to WhatsApp Web if the page became unhealthy
        (e.g. browser idle timeout, network blip).
        """
        self.logger.warning("Page unhealthy — reconnecting to WhatsApp Web…")
        try:
            self._page.goto(WHATSAPP_URL, timeout=30_000, wait_until="domcontentloaded")
            self._page.wait_for_timeout(PAGE_SETTLE_MS)
            self._page.wait_for_selector(
                '[data-testid="chat-list"], #pane-side, [aria-label="Chat list"]',
                timeout=CHAT_LOAD_TIMEOUT,
            )
            self.logger.info("Reconnected to WhatsApp Web successfully.")
        except Exception as exc:
            self.logger.error(f"Reconnection failed: {exc}")
            raise

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _dedup_key(sender: str, message: str) -> str:
        """
        Build a stable deduplication key from sender + first 80 chars of message.
        Collapses whitespace so minor rendering differences don't create duplicates.
        """
        norm_msg = re.sub(r"\s+", " ", message.strip())[:80].lower()
        return f"{sender.strip().lower()}::{norm_msg}"

    @staticmethod
    def _safe_filename(text: str, max_len: int = 30) -> str:
        """Replace filesystem-unsafe characters and truncate."""
        return re.sub(r"[^\w\s-]", "_", text).strip()[:max_len]

    # ── WhatsApp Web scraping ─────────────────────────────────────────────────

    def _extract_chats(self) -> list[dict]:
        """
        Evaluate the JS extractor against the live WhatsApp Web DOM.
        Returns a list of chat dicts (sender, message, hasUnread, …).
        """
        if not self._page_is_healthy():
            self._reconnect()

        try:
            chats = self._page.evaluate(_JS_EXTRACT_CHATS, KEYWORDS)
            return chats or []
        except Exception as exc:
            self.logger.error(f"JS extraction error: {exc}")
            return []

    # ── BaseWatcher interface ─────────────────────────────────────────────────

    def fetch_items(self) -> list:
        """
        Poll WhatsApp Web for unread chats or keyword-matched message previews.
        Filters out chats already processed this session.
        Returns a list of new chat dicts with an added _dedup_key field.
        """
        chats     = self._extract_chats()
        new_items = []

        for chat in chats:
            key = self._dedup_key(chat["sender"], chat["message"])
            if key not in self._processed_ids:
                chat["_dedup_key"] = key
                new_items.append(chat)

        return new_items

    def process_item(self, chat: dict) -> str | None:
        """
        Convert one WhatsApp chat entry into a structured Obsidian task file.

        File:   Needs_Action/WHATSAPP_[sender]_[YYYYmmdd_HHMMSS].md
        Returns filename on success, None on error.
        """
        dedup_key = chat.get("_dedup_key", "")
        if dedup_key in self._processed_ids:
            return None

        sender   = chat.get("sender", "Unknown")
        message  = chat.get("message", "")
        unread   = chat.get("unreadCount", "?")
        keyword  = chat.get("matchedKeyword")

        now     = datetime.now()
        ts_str  = now.strftime("%Y-%m-%d %H:%M:%S")
        ts_file = now.strftime("%Y%m%d_%H%M%S")

        safe_sender = self._safe_filename(sender)
        filename    = f"WHATSAPP_{safe_sender}_{ts_file}.md"
        filepath    = self.needs_action / filename

        # ── Priority: urgent if keyword is high-alert or chat has unread ──────
        if keyword and keyword in URGENT_KEYWORDS:
            priority = "high"
        elif chat.get("hasUnread"):
            priority = "high"
        elif keyword:
            priority = "medium"
        else:
            priority = "low"

        # ── Trigger description for YAML + table ─────────────────────────────
        if keyword:
            trigger = f"keyword: {keyword}"
        else:
            trigger = f"unread ({unread} message(s))"

        # ── Sanitize strings for YAML (remove stray quotes) ──────────────────
        sender_yaml  = sender.replace('"', "'")
        message_yaml = re.sub(r"\s+", " ", message).replace('"', "'").strip()

        # ── File content ──────────────────────────────────────────────────────
        content = f"""\
---
type: whatsapp
from: "{sender_yaml}"
message: "{message_yaml}"
time: {ts_str}
priority: {priority}
status: pending
unread_count: {unread}
trigger: {trigger}
source: whatsapp_web
created: {ts_str}
---

## WhatsApp Message from {sender}

| Field          | Value |
|----------------|-------|
| **From**       | {sender} |
| **Time**       | {ts_str} |
| **Unread**     | {unread} |
| **Trigger**    | {trigger} |
| **Priority**   | {priority} |

---

### Message Preview

> {message if message else "_No preview — open WhatsApp to read the full message._"}

---

### Suggested Actions

- [ ] Reply with quote
- [ ] Ask for details
- [ ] Archive chat
- [ ] Schedule follow-up call or meeting
- [ ] Delegate to team member
- [ ] Mark as done → move this file to Done/

---

*Created by {AGENT_SIGNATURE}*
*Logged at: {ts_str}*
"""

        try:
            filepath.write_text(content, encoding="utf-8")
        except OSError as exc:
            self.logger.error(f"Could not write {filename}: {exc}")
            return None

        # Record as processed only after the file is successfully written
        self._processed_ids.add(dedup_key)

        preview_short = (message[:57] + "…") if len(message) > 60 else message
        self.logger.info(
            f"  CREATED  {filename}\n"
            f"           From    : {sender}\n"
            f"           Trigger : {trigger}\n"
            f"           Preview : {preview_short}"
        )
        return filename

    # ── Watch loop override (adds browser cleanup) ────────────────────────────

    def watch(self) -> None:
        """
        Run the polling loop (inherited from BaseWatcher).
        Ensures the browser is closed cleanly on exit or error.
        """
        try:
            super().watch()
        finally:
            self.close()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the Playwright browser context and stop the Playwright engine."""
        try:
            if self._browser_context:
                self._browser_context.close()
                self._browser_context = None
                self.logger.info("Browser context closed.")
        except Exception as exc:
            self.logger.debug(f"Browser close error (ignored): {exc}")

        try:
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
                self.logger.info("Playwright engine stopped.")
        except Exception as exc:
            self.logger.debug(f"Playwright stop error (ignored): {exc}")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """
    CLI entry point.

    Usage:
        python whatsapp_watcher.py <vault_path>
        python whatsapp_watcher.py <vault_path> --reset-session
    """
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(
            "\nUsage:\n"
            "  python whatsapp_watcher.py <vault_path>\n"
            "  python whatsapp_watcher.py <vault_path> --reset-session\n\n"
            "Examples:\n"
            "  python whatsapp_watcher.py /mnt/c/projects/ai_employee/bronze\n"
            "  python whatsapp_watcher.py /mnt/c/projects/ai_employee/bronze --reset-session\n\n"
            "Flags:\n"
            "  --reset-session   Delete saved session and force a new QR scan.\n"
        )
        sys.exit(0)

    vault_path   = args[0]
    reset_session = "--reset-session" in args

    # ── Validate vault path ───────────────────────────────────────────────────
    if not os.path.isdir(vault_path):
        print(f"\nERROR: Vault path does not exist: {vault_path}\n")
        sys.exit(1)

    # ── Optional: clear saved session before starting ─────────────────────────
    if reset_session:
        marker = Path(vault_path) / "whatsapp_session" / SESSION_MARKER
        if marker.exists():
            marker.unlink()
            print(f"Session marker removed: {marker}")
            print("A new QR scan will be required on startup.\n")
        else:
            print("No session marker found — nothing to reset.\n")

    # ── Print startup summary ─────────────────────────────────────────────────
    print("=" * 62)
    print(f"  {AGENT_SIGNATURE}")
    print(f"  Vault    : {vault_path}")
    print(f"  Keywords : {', '.join(KEYWORDS)}")
    print(f"  Interval : {POLL_INTERVAL}s  |  Ctrl+C to stop")
    print("=" * 62)

    # ── Launch watcher ────────────────────────────────────────────────────────
    watcher = WhatsAppWatcher(vault_path=vault_path, interval=POLL_INTERVAL)
    watcher.watch()


if __name__ == "__main__":
    main()
