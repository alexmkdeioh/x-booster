"""
X (Twitter) Multi-Account Automation Engine
Supports:
1. Like Tweet
2. Like & Comment on Tweet
3. Space Listener (Presence Booster)
4. Space Listener + Like & Comment

Fault-tolerant: if one token/account fails, it skips it and keeps all other accounts running!
"""

import sys
import os
import random
import asyncio

# Ensure UTF-8 output on all operating systems including Windows charmap consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.async_api import async_playwright

DEBUG_DIR = os.path.join(os.path.dirname(__file__), "debug_screenshots")
os.makedirs(DEBUG_DIR, exist_ok=True)

DEFAULT_COMMENTS = [
    "Great post! 🔥",
    "Totally agree with this! 👏",
    "Thanks for sharing! 🚀",
    "100% on point 🙌",
    "Awesome perspective! ✨",
    "Love this! ❤️",
    "Very insightful! 💡",
    "Couldn't agree more! 👍",
    "Bullish on this! 📈",
    "Spot on! 🎯"
]

def get_tokens():
    # Support loading tokens from environment variable X_TOKENS (for public repo / cloud deployments)
    env_tokens = os.environ.get("X_TOKENS")
    if env_tokens:
        parsed = [t.strip() for t in env_tokens.replace(",", "\n").splitlines() if t.strip() and not t.startswith("#")]
        if parsed:
            return parsed

    tokens_file = os.path.join(os.path.dirname(__file__), "tokens.txt")
    if not os.path.exists(tokens_file):
        print("[-] tokens.txt not found and X_TOKENS env variable is not set!")
        return []
    with open(tokens_file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def get_comments():
    comments_file = os.path.join(os.path.dirname(__file__), "comments.txt")
    if not os.path.exists(comments_file):
        return DEFAULT_COMMENTS
    with open(comments_file, "r", encoding="utf-8") as f:
        comments = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return comments if comments else DEFAULT_COMMENTS

async def dismiss_popups(page):
    """Dismiss common Twitter popups like 'Review your email', cookie banners, etc."""
    popup_selectors = [
        'button:has-text("Yes, that\'s correct")',
        'button:has-text("Accept all cookies")',
        'button:has-text("Refuse non-essential cookies")',
        'button:has-text("Got it")',
        'button:has-text("Not now")',
        'button:has-text("Dismiss")',
        '[aria-label="Close"]',
        'div[role="button"]:has-text("Got it")'
    ]
    for sel in popup_selectors:
        try:
            loc = page.locator(sel)
            if await loc.count() > 0:
                for i in range(await loc.count()):
                    btn = loc.nth(i)
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.5)
                        break
        except Exception:
            pass

async def perform_like(page, index, token_preview):
    """Likes the tweet on the current page with robust retries and verification."""
    try:
        # Wait up to 15 seconds for the tweet action buttons to hydrate
        try:
            await page.wait_for_selector('[data-testid="like"], [data-testid="unlike"]', timeout=15000)
        except Exception:
            pass

        # 1. Check if already liked
        unlike_btn = page.locator('[data-testid="unlike"]').first
        if await unlike_btn.count() > 0 and await unlike_btn.is_visible():
            print(f"[OK] [Account #{index} | {token_preview}] Tweet is already liked!")
            return True

        # 2. Find like button on the primary tweet or anywhere on page
        like_btn = page.locator('article[data-testid="tweet"]').first.locator('[data-testid="like"]')
        if await like_btn.count() == 0 or not await like_btn.is_visible():
            like_btn = page.locator('[data-testid="like"]').first

        if await like_btn.count() > 0 and await like_btn.is_visible():
            await like_btn.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)

            # Try clicking normal, then force if needed
            try:
                await like_btn.click(timeout=5000)
            except Exception:
                await like_btn.click(force=True)

            await asyncio.sleep(1.5)

            # Verification: Check if unlike button is now visible
            confirmed_unlike = page.locator('[data-testid="unlike"]').first
            if await confirmed_unlike.count() > 0 and await confirmed_unlike.is_visible():
                print(f"[+] [Account #{index} | {token_preview}] Successfully liked the tweet! (Confirmed)")
                return True
            else:
                print(f"[+] [Account #{index} | {token_preview}] Like button clicked successfully!")
                return True
        else:
            print(f"[!] [Account #{index} | {token_preview}] Like button not found or not visible.")
            return False
    except Exception as e:
        print(f"[!] [Account #{index} | {token_preview}] Error liking tweet: {e}")
        return False

async def perform_comment(page, comment_text, index, token_preview):
    """Posts a comment / reply to the tweet on the current page."""
    try:
        print(f"[*] [Account #{index} | {token_preview}] Attempting to comment: \"{comment_text}\"...")
        posted = False

        # Wait up to 10 seconds for tweet or reply components
        try:
            await page.wait_for_selector('[data-testid="tweetTextarea_0"], [data-testid="reply"]', timeout=10000)
        except Exception:
            pass

        # Strategy 1: Check if inline tweet textarea is visible
        inline_textarea = page.locator('[data-testid="tweetTextarea_0"]').first
        if await inline_textarea.count() > 0 and await inline_textarea.is_visible():
            await inline_textarea.scroll_into_view_if_needed()
            await inline_textarea.click()
            await asyncio.sleep(0.5)
            
            try:
                await inline_textarea.fill(comment_text)
            except Exception:
                await page.keyboard.type(comment_text, delay=35)

            await asyncio.sleep(1)

            submit_btn = page.locator('[data-testid="tweetButtonInline"]').first
            if await submit_btn.count() == 0 or not await submit_btn.is_visible():
                submit_btn = page.locator('[data-testid="tweetButton"]').first

            if await submit_btn.count() > 0 and await submit_btn.is_visible():
                await submit_btn.click()
                posted = True

        # Strategy 2: Click the Reply icon button to open reply dialog
        if not posted:
            primary_tweet = page.locator('article[data-testid="tweet"]').first
            reply_btn = primary_tweet.locator('[data-testid="reply"]')
            if await reply_btn.count() == 0 or not await reply_btn.is_visible():
                reply_btn = page.locator('[data-testid="reply"]').first

            if await reply_btn.count() > 0 and await reply_btn.is_visible():
                await reply_btn.scroll_into_view_if_needed()
                await reply_btn.click()
                await asyncio.sleep(1.5)

                modal_textarea = page.locator('[data-testid="tweetTextarea_0"]').first
                if await modal_textarea.count() > 0 and await modal_textarea.is_visible():
                    await modal_textarea.click()
                    await asyncio.sleep(0.5)
                    try:
                        await modal_textarea.fill(comment_text)
                    except Exception:
                        await page.keyboard.type(comment_text, delay=35)

                    await asyncio.sleep(1)
                    tweet_btn = page.locator('[data-testid="tweetButton"]').first
                    if await tweet_btn.count() > 0 and await tweet_btn.is_visible():
                        await tweet_btn.click()
                        posted = True

        if posted:
            await asyncio.sleep(2.5)
            print(f"[+] [Account #{index} | {token_preview}] Successfully commented: \"{comment_text}\"")
            return True
        else:
            print(f"[!] [Account #{index} | {token_preview}] Reply box/button not found.")
            return False
    except Exception as e:
        print(f"[!] [Account #{index} | {token_preview}] Error commenting: {e}")
        return False

async def join_space_as_listener(page, index, token_preview):
    """Finds and clicks 'Start listening' or 'Listen' button for Spaces."""
    selectors = [
        'button:has-text("Start listening")',
        'div[role="button"]:has-text("Start listening")',
        'button:has-text("Listen")',
        'button:has-text("Join as listener")',
        'button:has-text("Tune in")',
        '[aria-label*="listening" i]',
        '[aria-label*="Listen" i]',
        'div[role="button"]:has-text("Listen")',
        'div[role="button"]:has-text("Join as listener")',
        '[data-testid="join-space-button"]',
        '[data-testid="audiospace-listen-button"]'
    ]

    clicked = False
    for attempt in range(12):
        for sel in selectors:
            try:
                locator = page.locator(sel)
                count = await locator.count()
                if count > 0:
                    for i in range(count):
                        btn = locator.nth(i)
                        if await btn.is_visible():
                            await btn.click()
                            clicked = True
                            print(f"[+] [Account #{index} | {token_preview}] Successfully joined Space: {sel}")
                            break
                if clicked:
                    break
            except Exception:
                continue
        if clicked:
            break
        await asyncio.sleep(2)

    return clicked

async def run_account_session(browser, token_entry, target_url, mode, comment_text, index):
    """
    Mode:
    1 = Like
    2 = Like & Comment
    3 = Space Listener Only
    4 = Space Listener + Like & Comment
    """
    if ":" in token_entry:
        auth_token, ct0 = token_entry.split(":", 1)
    else:
        auth_token = token_entry
        ct0 = None

    token_preview = f"{auth_token[:8]}..." if len(auth_token) >= 8 else auth_token

    # Slight human-like stagger between account startups (1-2 seconds)
    stagger_delay = (index - 1) * 1.5
    if stagger_delay > 0:
        await asyncio.sleep(stagger_delay)

    context = None
    try:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            permissions=["microphone"]
        )

        # Set cookies for both x.com and twitter.com
        cookies = [
            {
                "name": "auth_token",
                "value": auth_token,
                "domain": ".x.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "None"
            },
            {
                "name": "auth_token",
                "value": auth_token,
                "domain": ".twitter.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "None"
            }
        ]
        if ct0:
            cookies.extend([
                {
                    "name": "ct0",
                    "value": ct0,
                    "domain": ".x.com",
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax"
                },
                {
                    "name": "ct0",
                    "value": ct0,
                    "domain": ".twitter.com",
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax"
                }
            ])

        await context.add_cookies(cookies)
        page = await context.new_page()

        action_names = {1: "Like", 2: "Like & Comment", 3: "Space Listener", 4: "Space Listener + Like & Comment"}
        print(f"[*] [Account #{index} | {token_preview}] Running '{action_names.get(mode, 'Custom')}' on: {target_url}")

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"[!] [Account #{index} | {token_preview}] Page load failed: {e}")
            await context.close()
            return False

        # Let dynamic page content hydrate
        await asyncio.sleep(5)
        await dismiss_popups(page)

        # Check for logout / invalid auth
        try:
            body_text = await page.inner_text("body", timeout=5000)
            if "Sign in to X" in body_text or "Log in to Twitter" in body_text:
                print(f"[!] [Account #{index} | {token_preview}] WARNING: Not logged in! auth_token may be invalid or expired.")
        except Exception:
            pass

        account_success = True

        # Perform Space listening if mode is 3 or 4
        if mode in (3, 4):
            joined = await join_space_as_listener(page, index, token_preview)
            if joined:
                print(f"[+] [Account #{index} | {token_preview}] Listening and maintaining presence.")
            else:
                print(f"[?] [Account #{index} | {token_preview}] Space button not clicked.")
                account_success = False

        # Perform Like if mode is 1, 2, or 4
        if mode in (1, 2, 4):
            await dismiss_popups(page)
            liked = await perform_like(page, index, token_preview)
            if not liked:
                account_success = False

        # Perform Comment if mode is 2 or 4
        if mode in (2, 4):
            await dismiss_popups(page)
            commented = await perform_comment(page, comment_text, index, token_preview)
            if not commented:
                account_success = False

        # Save debug screenshot for verification
        screenshot_path = os.path.join(DEBUG_DIR, f"account_{index}_result.png")
        try:
            await page.screenshot(path=screenshot_path)
            print(f"[*] [Account #{index} | {token_preview}] Saved screenshot to: debug_screenshots/account_{index}_result.png")
        except Exception:
            pass

        # If mode was only Like or Like & Comment (modes 1 or 2), the job is done
        if mode in (1, 2):
            print(f"[OK] [Account #{index} | {token_preview}] All requested actions completed.")
            await asyncio.sleep(2)
            await context.close()
            return account_success

        # If mode was Space listener (modes 3 or 4), keep session alive
        if mode in (3, 4):
            print(f"[+] [Account #{index} | {token_preview}] Session active. Keeping presence alive...")
            while True:
                await asyncio.sleep(30)

    except Exception as e:
        print(f"[!] [Account #{index} | {token_preview}] Encountered an issue: {e}")
        if context:
            try:
                await context.close()
            except Exception:
                pass
        return False

def parse_cli_args():
    """
    Parses CLI arguments if provided:
    python space_listener_browser_bot.py [MODE] [URL] [COMMENT]
    Or flags: --mode, --url, --comment
    """
    mode = None
    url = None
    comment = None

    args = sys.argv[1:]
    if not args:
        return None, None, None

    if "--mode" in args:
        idx = args.index("--mode")
        if idx + 1 < len(args):
            mode = args[idx + 1]
    if "--url" in args:
        idx = args.index("--url")
        if idx + 1 < len(args):
            url = args[idx + 1]
    if "--comment" in args:
        idx = args.index("--comment")
        if idx + 1 < len(args):
            comment = args[idx + 1]

    if mode is None and len(args) >= 1:
        first = args[0].strip()
        if first in ("1", "2", "3", "4", "like", "comment", "listen", "all"):
            mode = first
            if len(args) >= 2:
                url = args[1].strip()
            if len(args) >= 3:
                comment = " ".join(args[2:]).strip()
        elif first.startswith("http://") or first.startswith("https://"):
            url = first
            mode = "3"
            if len(args) >= 2:
                comment = args[1]

    return mode, url, comment

def interactive_menu():
    """Interactive CLI menu to choose action, enter URL, and custom comment."""
    print("=" * 65)
    print("            X (TWITTER) MULTI-ACCOUNT ENGAGEMENT SUITE")
    print("=" * 65)
    print("  [1] Like Tweet")
    print("  [2] Like & Comment on Tweet")
    print("  [3] Space Listener (Presence Booster Only)")
    print("  [4] Space Listener + Like & Comment")
    print("=" * 65)

    choice = input("Enter choice [1-4] (default: 1): ").strip()
    if choice not in ("1", "2", "3", "4"):
        choice = "1"
    mode = int(choice)

    url_prompt = "Enter Tweet URL: " if mode in (1, 2) else "Enter Space or Tweet URL: "
    target_url = input(url_prompt).strip()
    while not target_url:
        print("[-] URL cannot be empty!")
        target_url = input(url_prompt).strip()

    custom_comment = None
    if mode in (2, 4):
        print("\n[*] Comment Option:")
        print("    - Type your custom comment, OR")
        print("    - Press ENTER to auto-load comments from comments.txt")
        entered = input("Comment: ").strip()
        if entered:
            custom_comment = entered

    return mode, target_url, custom_comment

async def main():
    cli_mode, cli_url, cli_comment = parse_cli_args()

    mode_map = {"like": 1, "comment": 2, "listen": 3, "all": 4}
    if cli_mode is not None:
        if isinstance(cli_mode, str) and cli_mode.lower() in mode_map:
            mode = mode_map[cli_mode.lower()]
        else:
            try:
                mode = int(cli_mode)
            except ValueError:
                mode = 1
        target_url = cli_url
        custom_comment = cli_comment
    else:
        mode, target_url, custom_comment = interactive_menu()

    tokens = get_tokens()
    if not tokens:
        print("[-] Please add at least 1 auth_token into tokens.txt (or set X_TOKENS env var)!")
        return

    file_comments = get_comments()

    action_names = {
        1: "LIKE TWEET",
        2: "LIKE & COMMENT ON TWEET",
        3: "SPACE LISTENER BOOSTER",
        4: "SPACE LISTENER + LIKE & COMMENT"
    }

    print("\n" + "=" * 65)
    print(f"  ACTION:       {action_names.get(mode, 'ENGAGEMENT')}")
    print(f"  ACCOUNTS:     {len(tokens)} account(s)")
    print(f"  TARGET URL:   {target_url}")
    if mode in (2, 4):
        if custom_comment:
            print(f"  COMMENT:      \"{custom_comment}\" (All accounts)")
        else:
            print(f"  COMMENTS:     Loaded from comments.txt ({len(file_comments)} template(s))")
    print("=" * 65 + "\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu"
            ]
        )

        tasks = []
        for i, token in enumerate(tokens, 1):
            if custom_comment:
                comment_for_account = custom_comment
            else:
                comment_for_account = file_comments[(i - 1) % len(file_comments)]

            tasks.append(
                run_account_session(browser, token, target_url, mode, comment_for_account, i)
            )

        print(f"[*] All {len(tokens)} account tasks dispatched. Working...\n")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        if mode in (1, 2):
            successes = sum(1 for r in results if r is True)
            print(f"\n[OK] Completed for {successes}/{len(tokens)} accounts!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Exiting. All sessions disconnected.")
