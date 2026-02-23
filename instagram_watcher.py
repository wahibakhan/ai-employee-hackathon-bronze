#!/usr/bin/env python3
"""
instagram_watcher.py — Instagram DM Watcher (Silver Tier)
==========================================================
Panaversity Personal AI Employee Hackathon 0 — Silver Tier

Monitors Instagram Direct Messages for unread messages and messages
containing business-critical keywords. Converts matching messages into
structured Obsidian task files in the vault's Needs_Action/ folder.

Agent Skill Pattern (extends BaseWatcher):
    fetch_items()      → Playwright → Instagram DMs DOM → keyword/unread threads
    process_item()     → write INSTAGRAM_[sender]_[ts].md to Needs_Action/
    update_dashboard() → log activity to Dashboard.md.md  (inherited)

Session Persistence:
    Session data stored in instagram_session/ (Chromium user-data-dir).
    First run  → headless=False — browser opens, login manually with
                  username + password. Instagram may ask 2FA — complete it.
    Subsequent → headless=True  — session restored silently from disk.

Usage:
    python instagram_watcher.py /mnt/c/projects/ai_employee/bronze

    # Force re-login (clear saved session):
    python instagram_watcher.py /mnt/c/projects/ai_employee/bronze --reset-session

Install:
    pip install playwright
    playwright install chromium

First run:
    A browser window opens at instagram.com. Enter your username and
    password. Complete any 2FA prompt. Once the DMs inbox is visible,
    the session is saved and all future runs are headless.

WSL Note:
    headless=False requires a display server.
    Windows 11 / WSLg : works out of the box (DISPLAY=:0 set automatically).
    Windows 10 / WSL2  : install VcXsrv, then: export DISPLAY=:0
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
        "Ensure base_watcher.py is in the same directory as instagram_watcher.py.\n"
    )
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────

# Business-critical keywords to watch for (case-insensitive)
KEYWORDS: list[str] = [
    "price", "quote", "design", "urgent", "invoice",
    "business", "help", "rate", "service",
]

# High-urgency keywords → priority: high in task file
URGENT_KEYWORDS: set[str] = {"urgent", "invoice", "help"}

POLL_INTERVAL     = 60        # seconds between Instagram DM checks
LOGIN_TIMEOUT     = 300       # seconds to wait for manual login
INBOX_TIMEOUT     = 30_000    # ms — wait for DM inbox to load
PAGE_SETTLE_MS    = 3_000     # ms — wait after navigation for SPA to render
SESSION_MARKER    = "ig_session_ok"
INSTAGRAM_URL     = "https://www.instagram.com"
INBOX_URL         = "https://www.instagram.com/direct/inbox/"
AGENT_SIGNATURE   = "Instagram Watcher — Panaversity AI Employee Hackathon Silver Tier"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ── JavaScript: extract unread/keyword DM threads from Instagram DOM ──────────
#
# Key insight from live testing: Instagram puts many [role="listbox"] elements
# on the page with aria-hidden="true" (search dropdowns etc). The real DM
# thread list is made up of <a href="/direct/t/[id]/"> anchor elements — one
# per conversation. This is stable across deploys and doesn't collide with
# hidden elements.
#
# Unread detection: Instagram bolds the sender name and preview for unread
# threads via computed font-weight >= 600, or places a blue dot SVG.
#
_JS_EXTRACT_DMS = """
(keywords) => {
    const results = [];
    const seen    = new Set();

    // ── Helper: check if element has bold computed font-weight ────────────────
    function isBold(el) {
        if (!el) return false;
        const fw = window.getComputedStyle(el).fontWeight;
        return fw === 'bold' || parseInt(fw, 10) >= 600;
    }

    // ── Primary: DM thread links — href="/direct/t/[thread_id]/" ─────────────
    // Each conversation in the inbox is an anchor with this href pattern.
    // This is the most reliable selector across Instagram builds.
    let items = [...document.querySelectorAll('a[href*="/direct/t/"]')];

    // ── Fallback: visible list items inside the inbox panel ──────────────────
    // Only used if no thread links found (e.g. different Instagram layout).
    if (!items.length) {
        items = [
            // Visible listbox only (exclude aria-hidden dropdowns/search boxes)
            ...document.querySelectorAll(
                '[role="listbox"]:not([aria-hidden="true"]) [role="option"]'
            ),
        ];
    }

    for (const item of items) {
        // ── Collect leaf text spans (no nested child elements) ────────────────
        const leafSpans = [...item.querySelectorAll('span')].filter(
            s => s.childElementCount === 0 && s.textContent.trim().length > 0
        );
        if (leafSpans.length < 1) continue;

        // ── Sender name: first meaningful span ───────────────────────────────
        const sender = (leafSpans[0]?.textContent || '').trim();
        if (!sender || seen.has(sender) || sender.length > 80) continue;

        // ── Message preview: first span that isn't the sender or a timestamp ──
        let preview = '';
        for (let i = 1; i < leafSpans.length; i++) {
            const t = leafSpans[i].textContent.trim();
            // Skip: empty, same as sender, short timestamps like "2h" / "Mon"
            if (t && t !== sender && t.length > 5 && !/^\\d+[smhd]$/.test(t)) {
                preview = t;
                break;
            }
        }

        // ── Unread: bold sender, bold preview, or Instagram blue dot ─────────
        const hasBoldSender  = isBold(leafSpans[0]);
        const hasBoldPreview = !!leafSpans.find(
            s => s.textContent.trim() === preview && isBold(s)
        );
        const hasUnreadDot = !!item.querySelector(
            'svg[aria-label*="nread"], ' +
            'div[style*="background-color: rgb(0, 149, 246)"], ' +
            'span[style*="background-color: rgb(0, 149, 246)"]'
        );
        const hasUnread = hasBoldSender || hasBoldPreview || hasUnreadDot;

        // ── Keyword match in preview ──────────────────────────────────────────
        const lowerPrev = preview.toLowerCase();
        const matched   = keywords.find(kw => lowerPrev.includes(kw.toLowerCase()));

        if (hasUnread || matched) {
            seen.add(sender);
            results.push({
                sender:         sender,
                message:        preview,
                hasUnread:      hasUnread,
                matchedKeyword: matched || null,
            });
        }
    }

    return results;
}
"""

# ── InstagramWatcher ──────────────────────────────────────────────────────────

class InstagramWatcher(BaseWatcher):
    """
    Silver Tier Instagram DM Watcher.

    Extends BaseWatcher to monitor Instagram Direct Messages for unread
    threads and keyword-matched message previews.

    Session flow:
        1. instagram_session/ig_session_ok exists → headless=True, resume.
        2. Otherwise → headless=False, browser opens at Instagram login page.
           User enters credentials (+ 2FA if enabled), and once the DM inbox
           is visible the session marker is written for future headless runs.

    Task file naming:  INSTAGRAM_[sender]_[YYYYmmdd_HHMMSS].md
    YAML frontmatter:  type, from, message, time, priority, status
    Body:              message preview + suggested action checkboxes
    """

    def __init__(self, vault_path: str, interval: int = POLL_INTERVAL) -> None:
        super().__init__(vault_path=vault_path, interval=interval, name="InstagramWatcher")

        # ── Session directory ─────────────────────────────────────────────────
        self.session_dir    = Path(vault_path) / "instagram_session"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_marker = self.session_dir / SESSION_MARKER

        # ── Playwright handles ────────────────────────────────────────────────
        self._playwright      = None
        self._browser_context = None
        self._page            = None

        self._start_browser()

    # ── Session helpers ───────────────────────────────────────────────────────

    def _session_exists(self) -> bool:
        return self.session_marker.exists()

    def _mark_session(self) -> None:
        self.session_marker.touch()
        self.logger.info(f"Session marker saved: {self.session_marker}")

    def _clear_session(self) -> None:
        self.session_marker.unlink(missing_ok=True)
        self.logger.info("Session marker removed — next run will require login.")

    # ── Browser lifecycle ─────────────────────────────────────────────────────

    def _start_browser(self) -> None:
        """
        Launch Playwright persistent Chromium context.

        headless=False on first run → user logs in manually.
        headless=True  on subsequent runs → session restored silently.
        """
        headless = self._session_exists()
        mode     = "headless" if headless else "headed  (manual login required)"
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
                    # Avoid Instagram detecting headless Chromium
                    "--disable-blink-features=AutomationControlled",
                ],
                viewport={"width": 1280, "height": 900},
                # Realistic desktop user-agent — Instagram is stricter than WhatsApp
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
        except Exception as exc:
            err = str(exc)
            if "display" in err.lower() or "DISPLAY" in err:
                self.logger.error(
                    "Cannot open browser — no display detected.\n"
                    "Windows 11 (WSLg): should work automatically.\n"
                    "Windows 10 (WSL2): install VcXsrv, then:\n"
                    "  export DISPLAY=:0"
                )
            else:
                self.logger.error(f"Browser launch failed: {exc}")
            self._playwright.stop()
            raise

        pages      = self._browser_context.pages
        self._page = pages[0] if pages else self._browser_context.new_page()

        # Navigate directly to the DM inbox
        self.logger.info(f"Navigating to {INBOX_URL} …")
        try:
            self._page.goto(INBOX_URL, timeout=30_000, wait_until="domcontentloaded")
        except Exception as exc:
            self.logger.error(f"Navigation failed: {exc}")
            self.close()
            raise

        self._page.wait_for_timeout(PAGE_SETTLE_MS)

        if not headless:
            self._handle_login()
        else:
            self._verify_session()

    def _dismiss_dialogs(self) -> None:
        """
        Dismiss Instagram's post-login pop-ups:
          - "Save your login info?"
          - "Turn on notifications"
          - Cookie consent banner
        These all have "Not Now" / "Decline" buttons.
        """
        for label in ["Not Now", "Not now", "Decline", "Allow all cookies"]:
            try:
                btn = self._page.get_by_role("button", name=label)
                if btn.is_visible():
                    btn.click()
                    self.logger.info(f"Dismissed dialog: '{label}'")
                    self._page.wait_for_timeout(800)
            except Exception:
                pass  # dialog wasn't there — that's fine

    def _handle_login(self) -> None:
        """
        Wait for the user to log in manually.

        Detects the login form and prints clear instructions. Blocks until the
        DM inbox is visible (login + any 2FA completed) or LOGIN_TIMEOUT expires.
        """
        self.logger.info("=" * 62)
        self.logger.info("  ACTION REQUIRED — Log in to Instagram in the browser:")
        self.logger.info("  1. Enter your username and password")
        self.logger.info("  2. Complete 2FA if prompted")
        self.logger.info("  3. Click 'Not Now' on any pop-ups")
        self.logger.info(f"  Waiting up to {LOGIN_TIMEOUT} seconds…")
        self.logger.info("=" * 62)

        # Confirm the login form is visible
        try:
            self._page.wait_for_selector(
                'input[name="username"], input[name="email"]',
                timeout=10_000,
            )
            self.logger.info("Login form detected — waiting for you to sign in…")
        except PWTimeoutError:
            # May already be redirected (e.g. session partially restored)
            self.logger.info("Login form not detected — checking for inbox directly…")

        # Wait until the browser navigates to the DM inbox URL.
        # URL check is the most reliable signal: Instagram redirects to
        # /direct/inbox/ only after a successful login + 2FA completion.
        try:
            self._page.wait_for_url(
                "**/direct/inbox/**",
                timeout=LOGIN_TIMEOUT * 1_000,
            )
        except PWTimeoutError:
            raise RuntimeError(
                f"Login timed out after {LOGIN_TIMEOUT}s.\n"
                "Please restart and complete the login within the time limit."
            )

        # Let the SPA render the conversation list before we start polling
        self._page.wait_for_timeout(PAGE_SETTLE_MS)

        # Dismiss any lingering pop-ups before proceeding
        self._dismiss_dialogs()
        self.logger.info("Login successful — DM inbox URL confirmed.")
        self._mark_session()

    def _verify_session(self) -> None:
        """
        Confirm the saved session is still valid (not logged out).
        If Instagram shows the login page, clear the marker and raise.
        """
        self.logger.info("Verifying saved session…")

        # Check URL — /direct/inbox/ means we're logged in and in the DMs.
        try:
            self._page.wait_for_url("**/direct/inbox/**", timeout=INBOX_TIMEOUT)
            self._page.wait_for_timeout(PAGE_SETTLE_MS)
            self.logger.info("Session valid — DM inbox URL confirmed.")
            self._dismiss_dialogs()
        except PWTimeoutError:
            login_visible = self._page.locator(
                'input[name="username"], input[name="email"]'
            ).is_visible()

            if login_visible:
                self._clear_session()
                raise RuntimeError(
                    "Instagram session expired — login page detected.\n"
                    "Session marker removed. Restart to log in again:\n"
                    "  python instagram_watcher.py <vault_path>"
                )
            else:
                self.logger.warning(
                    "DM inbox URL not confirmed within timeout — Instagram may be slow. "
                    "Will attempt polling anyway."
                )

    # ── Page health ───────────────────────────────────────────────────────────

    def _page_is_healthy(self) -> bool:
        try:
            return INSTAGRAM_URL in self._page.url
        except Exception:
            return False

    def _reconnect(self) -> None:
        """Re-navigate to DM inbox if the page became unhealthy."""
        self.logger.warning("Page unhealthy — reconnecting…")
        try:
            self._page.goto(INBOX_URL, timeout=30_000, wait_until="domcontentloaded")
            self._page.wait_for_url("**/direct/inbox/**", timeout=INBOX_TIMEOUT)
            self._page.wait_for_timeout(PAGE_SETTLE_MS)
            self._dismiss_dialogs()
            self.logger.info("Reconnected to Instagram DM inbox.")
        except Exception as exc:
            self.logger.error(f"Reconnection failed: {exc}")
            raise

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _dedup_key(sender: str, message: str) -> str:
        norm = re.sub(r"\s+", " ", message.strip())[:80].lower()
        return f"{sender.strip().lower()}::{norm}"

    @staticmethod
    def _safe_filename(text: str, max_len: int = 30) -> str:
        return re.sub(r"[^\w\s-]", "_", text).strip()[:max_len]

    # ── Instagram DOM scraping ────────────────────────────────────────────────

    def _extract_dms(self) -> list[dict]:
        """Run the JS extractor against the live Instagram DM inbox DOM."""
        if not self._page_is_healthy():
            self._reconnect()
        try:
            result = self._page.evaluate(_JS_EXTRACT_DMS, KEYWORDS)
            return result or []
        except Exception as exc:
            self.logger.error(f"JS extraction error: {exc}")
            return []

    # ── BaseWatcher interface ─────────────────────────────────────────────────

    def fetch_items(self) -> list:
        """
        Poll Instagram DM inbox for unread threads or keyword-matched previews.
        Returns only items not yet processed this session.
        """
        dms       = self._extract_dms()
        new_items = []
        for dm in dms:
            key = self._dedup_key(dm["sender"], dm["message"])
            if key not in self._processed_ids:
                dm["_dedup_key"] = key
                new_items.append(dm)
        return new_items

    def process_item(self, dm: dict) -> str | None:
        """
        Convert one Instagram DM thread entry into a structured Obsidian task.

        File:   Needs_Action/INSTAGRAM_[sender]_[YYYYmmdd_HHMMSS].md
        Returns filename on success, None on error.
        """
        dedup_key = dm.get("_dedup_key", "")
        if dedup_key in self._processed_ids:
            return None

        sender  = dm.get("sender", "Unknown")
        message = dm.get("message", "")
        keyword = dm.get("matchedKeyword")

        now     = datetime.now()
        ts_str  = now.strftime("%Y-%m-%d %H:%M:%S")
        ts_file = now.strftime("%Y%m%d_%H%M%S")

        safe_sender = self._safe_filename(sender)
        filename    = f"INSTAGRAM_{safe_sender}_{ts_file}.md"
        filepath    = self.needs_action / filename

        # ── Priority ──────────────────────────────────────────────────────────
        if keyword and keyword in URGENT_KEYWORDS:
            priority = "high"
        elif dm.get("hasUnread"):
            priority = "high"
        elif keyword:
            priority = "medium"
        else:
            priority = "low"

        # ── Trigger reason ────────────────────────────────────────────────────
        if keyword:
            trigger = f"keyword: {keyword}"
        else:
            trigger = "unread DM"

        # ── Sanitize for YAML ─────────────────────────────────────────────────
        sender_yaml  = sender.replace('"', "'")
        message_yaml = re.sub(r"\s+", " ", message).replace('"', "'").strip()

        content = f"""\
---
type: instagram
from: "{sender_yaml}"
message: "{message_yaml}"
time: {ts_str}
priority: {priority}
status: pending
trigger: {trigger}
source: instagram_dm
created: {ts_str}
---

## Instagram DM from {sender}

| Field        | Value |
|--------------|-------|
| **From**     | {sender} |
| **Time**     | {ts_str} |
| **Trigger**  | {trigger} |
| **Priority** | {priority} |

---

### Message Preview

> {message if message else "_No preview available — open Instagram to read the full message._"}

---

### Suggested Actions

- [ ] Reply with quote
- [ ] Ask for details
- [ ] Archive chat
- [ ] Schedule follow-up
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

        self._processed_ids.add(dedup_key)
        preview_short = (message[:57] + "…") if len(message) > 60 else message
        self.logger.info(
            f"  CREATED  {filename}\n"
            f"           From    : {sender}\n"
            f"           Trigger : {trigger}\n"
            f"           Preview : {preview_short}"
        )
        return filename

    # ── Watch loop override ───────────────────────────────────────────────────

    def watch(self) -> None:
        """Run the inherited poll loop; close browser cleanly on exit."""
        try:
            super().watch()
        finally:
            self.close()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def close(self) -> None:
        try:
            if self._browser_context:
                self._browser_context.close()
                self._browser_context = None
        except Exception as exc:
            self.logger.debug(f"Browser close error (ignored): {exc}")
        try:
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
        except Exception as exc:
            self.logger.debug(f"Playwright stop error (ignored): {exc}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(
            "\nUsage:\n"
            "  python instagram_watcher.py <vault_path>\n"
            "  python instagram_watcher.py <vault_path> --reset-session\n\n"
            "Examples:\n"
            "  python instagram_watcher.py /mnt/c/projects/ai_employee/bronze\n"
            "  python instagram_watcher.py /mnt/c/projects/ai_employee/bronze --reset-session\n\n"
            "Flags:\n"
            "  --reset-session   Delete saved session and force a new login.\n"
        )
        sys.exit(0)

    vault_path    = args[0]
    reset_session = "--reset-session" in args

    if not os.path.isdir(vault_path):
        print(f"\nERROR: Vault path does not exist: {vault_path}\n")
        sys.exit(1)

    # ── Optional session reset ────────────────────────────────────────────────
    if reset_session:
        marker = Path(vault_path) / "instagram_session" / SESSION_MARKER
        if marker.exists():
            marker.unlink()
            print(f"Session marker removed: {marker}")
            print("You will need to log in again on next start.\n")
        else:
            print("No session marker found — nothing to reset.\n")

    # ── Startup banner ────────────────────────────────────────────────────────
    print("=" * 62)
    print(f"  {AGENT_SIGNATURE}")
    print(f"  Vault    : {vault_path}")
    print(f"  Keywords : {', '.join(KEYWORDS)}")
    print(f"  Interval : {POLL_INTERVAL}s  |  Ctrl+C to stop")
    print("=" * 62)

    watcher = InstagramWatcher(vault_path=vault_path, interval=POLL_INTERVAL)
    watcher.watch()


if __name__ == "__main__":
    main()
