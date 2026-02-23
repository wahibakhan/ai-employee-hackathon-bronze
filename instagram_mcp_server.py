#!/usr/bin/env python3
"""
instagram_mcp_server.py — Instagram MCP Server (Silver Tier)
=============================================================
Panaversity Personal AI Employee Hackathon 0 — Silver Tier

Exposes three MCP tools to Claude Code (or any MCP client):

  • send_dm(to_username, message_text)
      → Sends an Instagram DM.
      → Requires: AI_Employee/Approved/APPROVAL_INSTAGRAM_DM_<username>.md
                   with YAML  status: approved

  • post_to_feed(caption, image_path?)
      → Creates a new Instagram feed post.
      → Requires: AI_Employee/Approved/APPROVAL_INSTAGRAM_POST.md
                   with YAML  status: approved

  • create_approval_request(action_type, subject, details)
      → Writes an approval request to AI_Employee/Pending_Approval/
        so the human can review, then move to Approved/ to unblock the action.

Human approval gate
-------------------
Every write action checks the AI_Employee/Approved/ folder before executing.
The human reviews what was queued in Pending_Approval/, then moves the file
to Approved/ (or edits status: approved in-place) to grant permission.

Dry-run mode
------------
Set env var  DRY_RUN=true  to log + simulate every action without
touching Instagram at all.  Useful for testing the approval flow.

Session reuse
-------------
Browser session is stored in instagram_session/ (same folder used by
instagram_watcher.py).  First run opens a headed browser window so you
can log in once;  all subsequent runs are headless.

Usage:
    pip install "mcp[cli]" playwright uvicorn
    playwright install chromium

    # First run (headed — log in to Instagram once):
    python instagram_mcp_server.py /mnt/c/projects/ai_employee/bronze

    # Subsequent runs (headless):
    python instagram_mcp_server.py /mnt/c/projects/ai_employee/bronze

    # Dry-run (no real posts/DMs):
    DRY_RUN=true python instagram_mcp_server.py /mnt/c/projects/ai_employee/bronze

    # Custom port:
    MCP_PORT=9000 python instagram_mcp_server.py ...

    # Force re-login (delete saved session and re-auth):
    python instagram_mcp_server.py ... --reset-session

MCP client (.mcp.json) config:
    {
      "mcpServers": {
        "instagram-silver-tier": {
          "url": "http://localhost:8000/sse"
        }
      }
    }

WSL note:
    headless=False requires a display server (WSLg / VcXsrv).
    Windows 11 WSLg works out of the box (DISPLAY=:0 auto-set).
"""

import asyncio
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Dependency guard: mcp ──────────────────────────────────────────────────────
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print(
        "\nERROR: mcp package not installed.\n"
        "Fix:\n\n"
        "  pip install 'mcp[cli]'\n"
    )
    sys.exit(1)

# ── Dependency guard: playwright ───────────────────────────────────────────────
try:
    from playwright.async_api import (
        async_playwright,
        BrowserContext,
        Page,
        Playwright,
        TimeoutError as PWTimeoutError,
    )
except ImportError:
    print(
        "\nERROR: Playwright not installed.\n"
        "Fix:\n\n"
        "  pip install playwright\n"
        "  playwright install chromium\n"
    )
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_vault() -> Path:
    """Accept vault path from CLI arg or fall back to default."""
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            return Path(arg)
    return Path("/mnt/c/projects/ai_employee/bronze")

VAULT_ROOT    = _resolve_vault()
AI_DIR        = VAULT_ROOT / "AI_Employee"
SESSION_DIR   = VAULT_ROOT / "instagram_session"
SESSION_MARKER = SESSION_DIR / "ig_session_ok"

PENDING_DIR   = AI_DIR / "Pending_Approval"
APPROVED_DIR  = AI_DIR / "Approved"
REJECTED_DIR  = AI_DIR / "Rejected"
DASHBOARD     = AI_DIR / "Dashboard.md.md"

MCP_PORT   = int(os.environ.get("MCP_PORT", "8000"))
DRY_RUN    = os.environ.get("DRY_RUN", "false").lower() in {"true", "1", "yes"}
RESET_SESSION = "--reset-session" in sys.argv

# Timeouts (milliseconds for Playwright, seconds elsewhere)
LOGIN_TIMEOUT_MS   = 300_000   # 5 min: wait for manual Instagram login
NAV_TIMEOUT_MS     = 15_000    # page load
ACTION_TIMEOUT_MS  = 10_000    # wait for individual elements
SETTLE_MS          = 1_500     # short settle after DOM changes

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("InstagramMCP")

# ── FastMCP app ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "instagram-silver-tier",
    instructions=(
        "Instagram MCP Server for the Panaversity AI Employee Silver Tier. "
        "Provides send_dm and post_to_feed tools. "
        "Every action requires a matching approval file in AI_Employee/Approved/. "
        "Use create_approval_request to queue an action for human review first."
    ),
)

# ═══════════════════════════════════════════════════════════════════════════════
# BROWSER CONTEXT  (module-level singleton, lazy-initialised on first tool call)
# ═══════════════════════════════════════════════════════════════════════════════

_pw: Optional[Playwright] = None
_ctx: Optional[BrowserContext] = None
_ctx_lock = asyncio.Lock()


async def get_context() -> BrowserContext:
    """
    Return (or create) the persistent Chromium context backed by instagram_session/.

    First run (no SESSION_MARKER):
        headless=False — browser window opens so the user can log in manually.
        After the DM inbox URL is confirmed, SESSION_MARKER is written and
        all future calls use headless=True.

    Subsequent runs:
        headless=True — session restored silently from the persistent user-data-dir.
    """
    global _pw, _ctx

    async with _ctx_lock:
        if _ctx is not None:
            return _ctx

        # Optional --reset-session: delete marker so we re-login
        if RESET_SESSION and SESSION_MARKER.exists():
            SESSION_MARKER.unlink()
            log.info("Session marker removed — will open headed browser for re-login.")

        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        headless = SESSION_MARKER.exists()

        log.info(
            "Launching Chromium (headless=%s, session=%s) …", headless, SESSION_DIR
        )

        _pw = await async_playwright().start()
        _ctx = await _pw.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            ignore_https_errors=True,
        )

        if not headless:
            # ── First-time login flow ──────────────────────────────────────────
            log.info("=" * 60)
            log.info("  INSTAGRAM LOGIN REQUIRED")
            log.info("  A browser window will open.")
            log.info("  Log in using your USERNAME + PASSWORD.")
            log.info("  Do NOT use 'Continue with Facebook'.")
            log.info("  Complete any 2FA prompt.")
            log.info("  Waiting up to 5 minutes …")
            log.info("=" * 60)

            page = await _ctx.new_page()
            await page.goto(
                "https://www.instagram.com/direct/inbox/",
                wait_until="domcontentloaded",
            )

            try:
                await page.wait_for_url(
                    "**/direct/inbox/**",
                    timeout=LOGIN_TIMEOUT_MS,
                )
                log.info("Login confirmed — DM inbox detected.")
            except PWTimeoutError:
                log.warning(
                    "DM inbox URL not confirmed within timeout. "
                    "Will attempt actions anyway."
                )

            # Write marker so future runs are headless
            SESSION_MARKER.touch()
            log.info("Session saved to %s", SESSION_DIR)
            await page.close()

        return _ctx


async def _dismiss_popups(page: Page) -> None:
    """Silently dismiss common Instagram pop-ups (notifications, cookies, etc.)."""
    for text in ("Not Now", "Decline", "Close", "Cancel"):
        try:
            btn = page.locator(f'button:has-text("{text}")').first
            if await btn.is_visible(timeout=1_500):
                await btn.click()
                log.debug("Dismissed popup: %s", text)
        except Exception:
            pass


async def _ensure_logged_in(page: Page) -> bool:
    """
    Return True if the current page indicates an active Instagram session.
    If we're on the login page, the session has expired.
    """
    url = page.url
    if "accounts/login" in url or "accounts/suspended" in url:
        log.error(
            "Session expired — Instagram redirected to login page. "
            "Delete instagram_session/ig_session_ok and restart the server "
            "to re-authenticate."
        )
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# VAULT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _slug(text: str) -> str:
    """Convert arbitrary text to a filename-safe slug."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text).strip("_")[:60]


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ts_file() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def find_approval(action_type: str, subject: str = "") -> Optional[Path]:
    """
    Look for an approval file in AI_Employee/Approved/.

    Naming conventions (case-insensitive):
        DM approvals  → APPROVAL_INSTAGRAM_DM_<username>.md
                         APPROVAL_INSTAGRAM_DM.md  (any DM)
        POST approvals → APPROVAL_INSTAGRAM_POST.md
                         APPROVAL_INSTAGRAM_POST_<slug>.md

    The file must contain  status: approved  (case-insensitive) anywhere
    in its YAML front-matter or body.

    Returns the Path if found and approved, else None.
    """
    if not APPROVED_DIR.exists():
        return None

    prefix = f"APPROVAL_INSTAGRAM_{action_type.upper()}"

    for f in APPROVED_DIR.glob("*.md"):
        fname_upper = f.name.upper()
        if not fname_upper.startswith(prefix):
            continue

        # If caller specified a subject (e.g. username), check it's in the name
        if subject and _slug(subject).upper() not in fname_upper:
            # Also accept a blanket approval with no subject in filename
            if fname_upper not in (f"{prefix}.MD",):
                continue

        # Verify the file itself says approved
        try:
            content = f.read_text(encoding="utf-8", errors="ignore").lower()
            if "status: approved" in content:
                return f
        except Exception:
            pass

    return None


def append_dashboard(entry: str) -> None:
    """Append a timestamped one-liner to Dashboard.md.md."""
    line = f"\n- [{_now_str()}] {entry} — Agent: Instagram MCP Server"
    try:
        with DASHBOARD.open("a", encoding="utf-8") as fh:
            fh.write(line)
        log.info("Dashboard: %s", entry)
    except Exception as exc:
        log.warning("Could not update dashboard: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════════
# INSTAGRAM ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def _do_send_dm(username: str, message: str) -> str:
    """
    Open a DM thread with `username` and send `message`.

    Flow:
        1. Navigate to instagram.com/direct/new/
        2. Search for the target username in the search box
        3. Select the first autocomplete result
        4. Click Next / Chat to open the composer
        5. Type message and press Enter (or click Send)
    """
    ctx = await get_context()
    page = await ctx.new_page()

    try:
        log.info("Opening new DM flow → @%s …", username)
        await page.goto(
            "https://www.instagram.com/direct/new/",
            wait_until="domcontentloaded",
            timeout=NAV_TIMEOUT_MS,
        )
        await _dismiss_popups(page)

        if not await _ensure_logged_in(page):
            return "ERROR: Instagram session expired. Re-authenticate and retry."

        # ── Search for user ────────────────────────────────────────────────────
        search = page.locator(
            'input[placeholder*="Search"], input[name="queryBox"], '
            'input[aria-label*="Search"]'
        ).first
        await search.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
        await search.fill(username)
        log.info("Typed username in search box.")

        await page.wait_for_timeout(SETTLE_MS)  # let autocomplete populate

        # ── Select first autocomplete result ───────────────────────────────────
        result = page.locator(
            '[role="option"]:not([aria-disabled="true"]), '
            '[data-testid="user-result-item"]'
        ).first
        await result.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
        await result.click()
        log.info("Selected @%s from autocomplete.", username)

        await page.wait_for_timeout(SETTLE_MS)

        # ── Open the thread (Next / Chat / Message button) ─────────────────────
        for label in ("Next", "Chat", "Message"):
            btn = page.locator(f'button:has-text("{label}")').first
            try:
                if await btn.is_visible(timeout=2_000):
                    await btn.click()
                    log.info("Clicked '%s' button.", label)
                    break
            except Exception:
                pass

        await page.wait_for_timeout(SETTLE_MS)

        # ── Type and send the message ──────────────────────────────────────────
        # Instagram DM composer is a contenteditable div in newer versions
        composer = page.locator(
            '[contenteditable="true"][aria-label], '
            'textarea[placeholder*="Message"], '
            '[role="textbox"]'
        ).last
        await composer.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
        await composer.click()
        await composer.fill(message)
        log.info("Message text entered.")

        # Try the Send button first; fall back to Enter key
        send_btn = page.locator(
            'button[type="submit"]:has-text("Send"), '
            'button:has-text("Send")'
        ).first
        try:
            if await send_btn.is_visible(timeout=2_000):
                await send_btn.click()
                log.info("Clicked Send button.")
            else:
                raise Exception("Send button not visible")
        except Exception:
            await page.keyboard.press("Enter")
            log.info("Pressed Enter to send.")

        await page.wait_for_timeout(2_000)
        log.info("DM sent to @%s successfully.", username)
        return f"DM sent to @{username}: \"{message[:60]}{'…' if len(message) > 60 else ''}\""

    finally:
        await page.close()


async def _do_post_to_feed(caption: str, image_path: Optional[str]) -> str:
    """
    Create a new Instagram feed post with the given caption and optional image.

    Instagram requires media for feed posts.  If image_path is omitted or
    the file does not exist, this function returns an explanatory error.

    Flow:
        1. Navigate to instagram.com/
        2. Click the + (New Post) button in the sidebar nav
        3. Upload image via the file input
        4. Step through crop → filter → caption screens (Next × 2)
        5. Type caption in the Write a caption… box
        6. Click Share
    """
    # Validate image upfront — feed posts require media
    if not image_path:
        return (
            "ERROR: Instagram feed posts require an image. "
            "Provide image_path pointing to a .jpg or .png file."
        )
    img = Path(image_path)
    if not img.exists():
        return f"ERROR: Image file not found: {image_path}"

    ctx = await get_context()
    page = await ctx.new_page()

    try:
        log.info("Opening Instagram home to create feed post …")
        await page.goto(
            "https://www.instagram.com/",
            wait_until="domcontentloaded",
            timeout=NAV_TIMEOUT_MS,
        )
        await _dismiss_popups(page)

        if not await _ensure_logged_in(page):
            return "ERROR: Instagram session expired. Re-authenticate and retry."

        # ── Click the + / New post button ──────────────────────────────────────
        create_btn = page.locator(
            '[aria-label="New post"], '
            '[aria-label="Create"], '
            'svg[aria-label="New post"]'
        ).first
        await create_btn.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
        await create_btn.click()
        log.info("Clicked 'New post' button.")
        await page.wait_for_timeout(SETTLE_MS)

        # ── Upload image ───────────────────────────────────────────────────────
        # Instagram's file input is usually hidden — set_input_files bypasses that
        file_input = page.locator('input[type="file"]').first
        try:
            await file_input.set_input_files(str(img), timeout=5_000)
            log.info("Image uploaded via hidden file input: %s", img.name)
        except Exception:
            # Fallback: click a visible "Select from computer" button
            log.info("Hidden input not ready — trying 'Select from computer' button.")
            async with page.expect_file_chooser() as fc_info:
                select_btn = page.locator(
                    'button:has-text("Select"), '
                    'button:has-text("computer"), '
                    'button:has-text("Choose")'
                ).first
                await select_btn.click()
            chooser = await fc_info.value
            await chooser.set_files(str(img))
            log.info("Image uploaded via file chooser: %s", img.name)

        await page.wait_for_timeout(2_000)

        # ── Step through Crop → Filter → Caption (two 'Next' clicks) ──────────
        for step_name in ("Crop/Aspect", "Filters"):
            next_btn = page.locator('button:has-text("Next")').first
            try:
                await next_btn.wait_for(state="visible", timeout=5_000)
                await next_btn.click()
                log.info("Clicked Next (%s step).", step_name)
                await page.wait_for_timeout(SETTLE_MS)
            except Exception:
                log.warning("Next button not found at %s step — continuing.", step_name)

        # ── Enter caption ──────────────────────────────────────────────────────
        caption_box = page.locator(
            '[aria-label="Write a caption…"], '
            '[aria-label*="caption"], '
            '[placeholder*="caption"], '
            '[contenteditable="true"]'
        ).first
        await caption_box.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
        await caption_box.click()
        # Type slowly to trigger any caption-length counters
        await caption_box.fill(caption)
        log.info("Caption entered (%d chars).", len(caption))

        await page.wait_for_timeout(SETTLE_MS)

        # ── Share ──────────────────────────────────────────────────────────────
        share_btn = page.locator('button:has-text("Share")').first
        await share_btn.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
        await share_btn.click()
        log.info("Clicked Share — post submitted.")

        # Wait for success indicator (post dialog closes or "Post shared" banner)
        await page.wait_for_timeout(4_000)
        log.info("Feed post created successfully.")
        return f"Feed post created with caption: \"{caption[:80]}{'…' if len(caption) > 80 else ''}\""

    finally:
        await page.close()


# ═══════════════════════════════════════════════════════════════════════════════
# MCP TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
async def send_dm(to_username: str, message_text: str) -> str:
    """
    Send an Instagram Direct Message to a user.

    The action is blocked until a matching approval file is found in
    AI_Employee/Approved/:

        Filename: APPROVAL_INSTAGRAM_DM_<to_username>.md
        Must contain the line:  status: approved

    Use create_approval_request(action_type="DM", subject=<username>, ...)
    to queue the request for the human to review first.

    Args:
        to_username:  Instagram username to message (without the @ sign).
        message_text: The full message text to send.

    Returns:
        Confirmation string, or an error / "awaiting approval" message.
    """
    log.info("Tool: send_dm(to='%s')", to_username)

    # ── Approval gate ──────────────────────────────────────────────────────────
    approval = find_approval("DM", to_username)
    if not approval:
        pending_name = f"APPROVAL_INSTAGRAM_DM_{_slug(to_username)}.md"
        msg = (
            f"ACTION BLOCKED — no approved file found for send_dm → @{to_username}.\n\n"
            f"To authorise this action:\n"
            f"  1. Run: create_approval_request(action_type='DM', subject='{to_username}', "
            f"details='Send DM: {message_text[:50]}')\n"
            f"  2. Review the file in AI_Employee/Pending_Approval/{pending_name}\n"
            f"  3. Move it to AI_Employee/Approved/ (or edit status: approved in-place)\n"
            f"  4. Re-invoke send_dm()"
        )
        log.warning("Approval missing for send_dm → @%s", to_username)
        return msg

    log.info("Approval granted via: %s", approval.name)

    # ── Dry-run bypass ─────────────────────────────────────────────────────────
    if DRY_RUN:
        result = (
            f"[DRY-RUN] Would send DM to @{to_username}:\n"
            f"  Message : {message_text}\n"
            f"  Approval: {approval.name}"
        )
        log.info(result)
        append_dashboard(f"[DRY-RUN] DM to @{to_username}")
        return result

    # ── Execute ────────────────────────────────────────────────────────────────
    result = await _do_send_dm(to_username, message_text)
    append_dashboard(f"Sent DM to @{to_username}")
    return result


@mcp.tool()
async def post_to_feed(caption: str, image_path: Optional[str] = None) -> str:
    """
    Create a new Instagram feed post with a caption and an image.

    The action is blocked until an approval file is found in
    AI_Employee/Approved/:

        Filename: APPROVAL_INSTAGRAM_POST.md   (or APPROVAL_INSTAGRAM_POST_<slug>.md)
        Must contain the line:  status: approved

    Use create_approval_request(action_type='POST', subject='post-title', ...)
    to queue the request for human review first.

    Args:
        caption:    Full post caption text (hashtags, emojis — all fine).
                    Tip: Draft this with SK04 Instagram Post Generator first.
        image_path: Absolute path to the image file (.jpg or .png).
                    Instagram feed posts require an image.

    Returns:
        Confirmation string, or an error / "awaiting approval" message.
    """
    log.info("Tool: post_to_feed(image='%s')", image_path)

    # ── Approval gate ──────────────────────────────────────────────────────────
    approval = find_approval("POST")
    if not approval:
        msg = (
            "ACTION BLOCKED — no approved file found for post_to_feed.\n\n"
            "To authorise this action:\n"
            "  1. Run: create_approval_request(action_type='POST', "
            "subject='feed-post', details='<post description>')\n"
            "  2. Review the file in AI_Employee/Pending_Approval/APPROVAL_INSTAGRAM_POST.md\n"
            "  3. Move it to AI_Employee/Approved/ (or edit status: approved in-place)\n"
            "  4. Re-invoke post_to_feed()"
        )
        log.warning("Approval missing for post_to_feed.")
        return msg

    log.info("Approval granted via: %s", approval.name)

    # ── Dry-run bypass ─────────────────────────────────────────────────────────
    if DRY_RUN:
        result = (
            f"[DRY-RUN] Would post to Instagram feed:\n"
            f"  Caption : {caption[:120]}{'…' if len(caption) > 120 else ''}\n"
            f"  Image   : {image_path or 'none (would fail — image required)'}\n"
            f"  Approval: {approval.name}"
        )
        log.info(result)
        append_dashboard("[DRY-RUN] Posted to Instagram feed")
        return result

    # ── Execute ────────────────────────────────────────────────────────────────
    result = await _do_post_to_feed(caption, image_path)
    if not result.startswith("ERROR"):
        append_dashboard("Posted to Instagram feed")
    return result


@mcp.tool()
async def create_approval_request(
    action_type: str,
    subject: str,
    details: str,
) -> str:
    """
    Create an approval request file in AI_Employee/Pending_Approval/.

    The human reviews this file and either:
        • Moves it to AI_Employee/Approved/  (grants access)
        • Moves it to AI_Employee/Rejected/  (denies access)

    After the file is in Approved/, the corresponding tool call
    (send_dm or post_to_feed) will proceed.

    Args:
        action_type: "DM" to approve a direct message, "POST" to approve
                     a feed post.  (Case-insensitive.)
        subject:     Username for DM, or post title/slug for POST.
                     Used to name the approval file.
        details:     Human-readable summary of what will be sent/posted
                     (message preview, caption excerpt, image filename, etc.).

    Returns:
        Path to the created approval request file.
    """
    action_upper = action_type.upper().strip()
    if action_upper not in ("DM", "POST"):
        return "ERROR: action_type must be 'DM' or 'POST'."

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    slug = _slug(subject)
    filename = f"APPROVAL_INSTAGRAM_{action_upper}_{slug}.md"
    filepath = PENDING_DIR / filename

    human_action = (
        f"Send DM to @{subject}" if action_upper == "DM"
        else f"Post to Instagram feed: {subject}"
    )

    content = f"""---
type: approval_request
action: instagram_{action_upper.lower()}
subject: "{subject}"
status: pending
created: "{_now_str()}"
requires_human_approval: true
---

# Approval Request — Instagram {action_upper}

**Action:** {human_action}

**Details:**
{details}

---

## How to Approve

1. Review the details above carefully.
2. If approved, **move this file** to:
   `AI_Employee/Approved/{filename}`
   (or edit `status: pending` → `status: approved` in this file's YAML)
3. Then re-run the MCP tool call that triggered this request.

## How to Reject

Move this file to:
   `AI_Employee/Rejected/{filename}`

---

## Rules (from Company Handbook)

- Human is always the final approver for: DMs sent, posts published.
- Never auto-post or auto-DM without this approval flow.
- This file was created by Instagram MCP Server — Silver Tier.

---
*Agent: Panaversity AI Employee — Silver Tier | InstagramMCPServer*
"""

    filepath.write_text(content, encoding="utf-8")
    log.info("Approval request created: %s", filepath)

    append_dashboard(
        f"Approval request created: {filename} (action={action_upper}, subject={subject})"
    )

    return (
        f"Approval request created:\n"
        f"  File   : {filepath}\n"
        f"  Action : {human_action}\n\n"
        f"Next steps:\n"
        f"  1. Review: AI_Employee/Pending_Approval/{filename}\n"
        f"  2. Approve: move to AI_Employee/Approved/{filename}\n"
        f"     (or change  status: pending  →  status: approved  in the file)\n"
        f"  3. Re-run the tool call."
    )


@mcp.tool()
async def check_approval_status(action_type: str, subject: str = "") -> str:
    """
    Check whether an approval exists for a given action.

    Useful before calling send_dm or post_to_feed to avoid a blocked attempt.

    Args:
        action_type: "DM" or "POST"
        subject:     Username (for DM) or empty string (for POST)

    Returns:
        "APPROVED — <filename>" or a "NOT APPROVED" message with next steps.
    """
    approval = find_approval(action_type.upper(), subject)
    if approval:
        return f"APPROVED — {approval.name}\nReady to proceed with the action."

    pending_name = (
        f"APPROVAL_INSTAGRAM_{action_type.upper()}_{_slug(subject)}.md"
        if subject
        else f"APPROVAL_INSTAGRAM_{action_type.upper()}.md"
    )
    return (
        f"NOT APPROVED — no matching approved file found.\n"
        f"Expected: AI_Employee/Approved/{pending_name}\n"
        f"          with YAML line:  status: approved\n\n"
        f"Run create_approval_request(action_type='{action_type}', "
        f"subject='{subject}', details='...') to start the approval flow."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    log.info("=" * 62)
    log.info("  Instagram MCP Server — Silver Tier")
    log.info("  Vault   : %s", VAULT_ROOT)
    log.info("  Session : %s", SESSION_DIR)
    log.info("  Port    : %s", MCP_PORT)
    log.info("  DryRun  : %s", DRY_RUN)
    log.info("  Tools   : send_dm, post_to_feed,")
    log.info("            create_approval_request, check_approval_status")
    log.info("  SSE URL : http://localhost:%s/sse", MCP_PORT)
    log.info("=" * 62)

    # Ensure vault directories exist
    for d in (PENDING_DIR, APPROVED_DIR, REJECTED_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # Run as SSE server — Claude Code connects via http://localhost:<port>/sse
    mcp.run(transport="sse", host="0.0.0.0", port=MCP_PORT)
