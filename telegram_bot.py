"""
Telegram Remote Controller for X (Twitter) Multi-Account Suite
Control your bots from anywhere in the world from your phone via Telegram!
Compatible with Render.com Free Web Service and local environments.
Includes automated Self-Ping Keep-Awake Engine and Interactive Buttons.
"""

import os
import sys
import json
import asyncio
import aiohttp
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import space_listener_browser_bot as bot_engine
from playwright.async_api import async_playwright

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "telegram_config.json")
DEBUG_DIR = os.path.join(os.path.dirname(__file__), "debug_screenshots")
os.makedirs(DEBUG_DIR, exist_ok=True)

# Global tracking
current_space_task = None
current_space_browser = None
keep_awake_task = None
configured_awake_url = None
user_state = {}  # Tracks conversation states like waiting for tweet URL

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("❤️ Like Tweet"), KeyboardButton("💬 Like & Comment")],
        [KeyboardButton("🎙️ Space Booster"), KeyboardButton("🛑 Stop Space")],
        [KeyboardButton("⚡ Keep Awake"), KeyboardButton("📊 Status")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"telegram_bot_token": "", "allowed_user_ids": []}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"telegram_bot_token": "", "allowed_user_ids": []}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def is_authorized(user_id):
    cfg = load_config()
    allowed = cfg.get("allowed_user_ids", [])
    env_allowed = os.environ.get("ALLOWED_USER_ID")
    if env_allowed:
        try:
            allowed.append(int(env_allowed))
        except ValueError:
            pass
    if not allowed:
        return True
    return user_id in allowed

async def health_check(request):
    return web.Response(text="X Booster Telegram Bot is online and healthy!", content_type="text/plain")

async def keep_awake_loop():
    """Continuously pings the web service every 9 minutes to prevent Render free tier from sleeping."""
    global configured_awake_url
    await asyncio.sleep(10)  # wait for web server to start up

    while True:
        target_url = configured_awake_url or os.environ.get("RENDER_EXTERNAL_URL")
        if target_url:
            if not target_url.endswith("/health"):
                ping_url = target_url.rstrip("/") + "/health"
            else:
                ping_url = target_url
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(ping_url, timeout=15) as resp:
                        print(f"[*] [Keep-Awake] Pinged {ping_url} - Status: {resp.status}")
            except Exception as e:
                print(f"[!] [Keep-Awake] Ping error: {e}")
        else:
            print("[*] [Keep-Awake] Waiting for URL (not set yet or running locally).")

        # Sleep for 9 minutes (540 seconds) - Render sleeps at 15 minutes
        await asyncio.sleep(540)

async def start_web_server(app):
    """Starts a lightweight web server for Render's free Web Service health checks."""
    port_str = os.environ.get("PORT", "8080")
    try:
        port = int(port_str)
    except ValueError:
        port = 8080

    server = web.Application()
    server.router.add_get("/", health_check)
    server.router.add_get("/health", health_check)

    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[*] Health web server started on port {port} (Render ready!)")

    # Start the keep-awake loop in background
    global keep_awake_task
    keep_awake_task = asyncio.create_task(keep_awake_loop())

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cfg = load_config()
    allowed = cfg.get("allowed_user_ids", [])

    if not allowed and not os.environ.get("ALLOWED_USER_ID"):
        cfg["allowed_user_ids"] = [user.id]
        save_config(cfg)

    if not is_authorized(user.id):
        await update.message.reply_text("⛔ Unauthorized. You do not have access to this bot.")
        return

    tokens = bot_engine.get_tokens()
    awake_url = configured_awake_url or os.environ.get("RENDER_EXTERNAL_URL", "Local PC Mode")

    msg = (
        f"👋 *Welcome to X Multi-Account Remote Controller!*\n\n"
        f"📊 *Connected Accounts:* `{len(tokens)}`\n"
        f"🌐 *Host Status:* `{awake_url}`\n\n"
        f"⚡ *Use the buttons below to control your accounts:* 👇\n\n"
        f"❤️ `Like Tweet` - Like any tweet\n"
        f"💬 `Like & Comment` - Like & comment on tweet\n"
        f"🎙️ `Space Booster` - Join Twitter Space as listener\n"
        f"🛑 `Stop Space` - Disconnect from Space\n"
        f"⚡ `Keep Awake` - Check & trigger 24/7 keep-alive ping\n"
        f"📊 `Status` - View accounts and active sessions\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def awake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Awake button / command handler."""
    if not is_authorized(update.effective_user.id):
        return

    global configured_awake_url

    # Check if user passed a custom URL (e.g. /awake https://myapp.onrender.com)
    if context.args:
        custom_url = context.args[0].strip()
        configured_awake_url = custom_url
        await update.message.reply_text(f"🌐 Keep-Awake URL set to:\n`{configured_awake_url}`", parse_mode="Markdown")

    target_url = configured_awake_url or os.environ.get("RENDER_EXTERNAL_URL")

    if not target_url:
        msg = (
            "⚡ *Keep-Awake Engine*\n\n"
            "ℹ️ *Status:* Running in local mode (Render URL not detected yet).\n\n"
            "If hosted on Render, you can manually set your URL by typing:\n"
            "`/awake https://your-service-name.onrender.com`\n\n"
            "Once set, the bot pings itself every 9 minutes so it **never sleeps**!"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())
        return

    # Trigger an immediate test ping
    ping_url = target_url.rstrip("/") + "/health"
    ping_status = "Unknown"
    latency = 0
    try:
        import time
        start_t = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(ping_url, timeout=10) as resp:
                latency = round((time.time() - start_t) * 1000)
                if resp.status == 200:
                    ping_status = f"✅ 200 OK ({latency}ms)"
                else:
                    ping_status = f"⚠️ HTTP {resp.status}"
    except Exception as e:
        ping_status = f"❌ Error: {e}"

    msg = (
        "⚡ *Keep-Awake 24/7 Engine is ACTIVE!*\n\n"
        f"🌐 *Target URL:* `{ping_url}`\n"
        f"📡 *Immediate Ping:* `{ping_status}`\n"
        "⏱️ *Auto-Ping Interval:* Every 9 minutes\n"
        "🟢 *Server State:* Render will NOT sleep!\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    tokens = bot_engine.get_tokens()
    comments = bot_engine.get_comments()
    global current_space_task

    is_space_running = current_space_task is not None and not current_space_task.done()
    target_url = configured_awake_url or os.environ.get("RENDER_EXTERNAL_URL", "Local PC (Active)")

    msg = (
        f"📊 *Bot Status Overview*\n\n"
        f"🔑 *Loaded Accounts:* `{len(tokens)}`\n"
        f"📝 *Comments in File:* `{len(comments)}`\n"
        f"🎙️ *Space Listener Active:* `{'Yes (Running)' if is_space_running else 'No (Idle)'}`\n"
        f"⚡ *Host / Keep-Awake:* `{target_url}`\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def run_engagement_task(chat_id, bot, mode, target_url, custom_comment=None):
    tokens = bot_engine.get_tokens()
    file_comments = bot_engine.get_comments()

    mode_name = "Like" if mode == 1 else "Like & Comment"
    await bot.send_message(
        chat_id=chat_id,
        text=f"⏳ *Starting {mode_name}...*\n\n🎯 *URL:* `{target_url}`\n👥 *Accounts:* `{len(tokens)}`",
        parse_mode="Markdown"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        tasks = []
        for i, token in enumerate(tokens, 1):
            if custom_comment:
                comment_text = custom_comment
            else:
                comment_text = file_comments[(i - 1) % len(file_comments)]

            tasks.append(
                bot_engine.run_account_session(browser, token, target_url, mode, comment_text, i)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        await browser.close()

    success_count = sum(1 for r in results if r is True)
    await bot.send_message(
        chat_id=chat_id,
        text=f"✅ *{mode_name} Finished!*\n\n🎉 Successfully completed for *{success_count}/{len(tokens)}* accounts.",
        parse_mode="Markdown"
    )

    first_screenshot = os.path.join(DEBUG_DIR, "account_1_result.png")
    if os.path.exists(first_screenshot):
        try:
            with open(first_screenshot, "rb") as photo:
                await bot.send_photo(chat_id=chat_id, photo=photo, caption="📸 Proof from Account #1")
        except Exception as e:
            print(f"Could not send photo: {e}")

async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    if not context.args:
        user_state[update.effective_user.id] = "waiting_for_like_url"
        await update.message.reply_text("❤️ *Send the Tweet URL you want to like:*", parse_mode="Markdown")
        return

    tweet_url = context.args[0].strip()
    tokens = bot_engine.get_tokens()
    if not tokens:
        await update.message.reply_text(
            "❌ *No accounts found!*\n\n"
            "• On your PC: Make sure `tokens.txt` has your tokens.\n"
            "• On Render: Go to Environment Variables and add `X_TOKENS` with your tokens.",
            parse_mode="Markdown"
        )
        return

    asyncio.create_task(run_engagement_task(update.effective_chat.id, context.bot, mode=1, target_url=tweet_url))

async def comment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    if not context.args:
        user_state[update.effective_user.id] = "waiting_for_comment_url"
        await update.message.reply_text(
            "💬 *Send the Tweet URL to Like & Comment:*\n\n*(You can also include your comment after the URL, e.g.:*\n`https://x.com/user/status/123 Amazing post! 🔥`)",
            parse_mode="Markdown"
        )
        return

    tweet_url = context.args[0].strip()
    custom_comment = " ".join(context.args[1:]).strip() if len(context.args) > 1 else None

    tokens = bot_engine.get_tokens()
    if not tokens:
        await update.message.reply_text(
            "❌ *No accounts found!*\n\n"
            "• On your PC: Make sure `tokens.txt` has your tokens.\n"
            "• On Render: Go to Environment Variables and add `X_TOKENS` with your tokens.",
            parse_mode="Markdown"
        )
        return

    asyncio.create_task(
        run_engagement_task(update.effective_chat.id, context.bot, mode=2, target_url=tweet_url, custom_comment=custom_comment)
    )

async def run_space_session(chat_id, bot, space_url):
    global current_space_browser
    tokens = bot_engine.get_tokens()

    await bot.send_message(
        chat_id=chat_id,
        text=f"🎙️ *Joining Space with {len(tokens)} accounts...*\n\n🔗 `{space_url}`",
        parse_mode="Markdown"
    )

    async with async_playwright() as p:
        current_space_browser = await p.chromium.launch(
            headless=True,
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        tasks = [
            bot_engine.run_account_session(current_space_browser, token, space_url, 3, "", i)
            for i, token in enumerate(tokens, 1)
        ]

        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ *All {len(tokens)} accounts dispatched!*\nMaintaining presence in Space. Tap `🛑 Stop Space` when you want them to leave.",
            parse_mode="Markdown"
        )

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        finally:
            if current_space_browser:
                try:
                    await current_space_browser.close()
                except Exception:
                    pass
                current_space_browser = None

async def space_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_space_task
    if not is_authorized(update.effective_user.id):
        return

    if not context.args:
        user_state[update.effective_user.id] = "waiting_for_space_url"
        await update.message.reply_text("🎙️ *Send the Space URL you want accounts to join:*", parse_mode="Markdown")
        return

    space_url = context.args[0].strip()
    if current_space_task and not current_space_task.done():
        await update.message.reply_text("⚠️ A Space session is already running! Tap `🛑 Stop Space` first.", parse_mode="Markdown")
        return

    current_space_task = asyncio.create_task(run_space_session(update.effective_chat.id, context.bot, space_url))

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_space_task, current_space_browser
    if not is_authorized(update.effective_user.id):
        return

    if current_space_task and not current_space_task.done():
        current_space_task.cancel()
        current_space_task = None
        if current_space_browser:
            try:
                await current_space_browser.close()
            except Exception:
                pass
            current_space_browser = None
        await update.message.reply_text("🛑 *Space session stopped.* All accounts disconnected.", parse_mode="Markdown")
    else:
        await update.message.reply_text("ℹ️ No active Space session is running.")

async def handle_button_or_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text messages and button clicks from the custom keyboard."""
    if not is_authorized(update.effective_user.id):
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id

    # Handle button taps
    if text == "❤️ Like Tweet":
        user_state[user_id] = "waiting_for_like_url"
        await update.message.reply_text("❤️ *Send the Tweet URL you want to like:*", parse_mode="Markdown")
        return
    elif text == "💬 Like & Comment":
        user_state[user_id] = "waiting_for_comment_url"
        await update.message.reply_text(
            "💬 *Send the Tweet URL:*\n\n*(Optionally add your comment after the URL, or just send the URL to use comments.txt)*",
            parse_mode="Markdown"
        )
        return
    elif text == "🎙️ Space Booster":
        user_state[user_id] = "waiting_for_space_url"
        await update.message.reply_text("🎙️ *Send the Space URL to join:*", parse_mode="Markdown")
        return
    elif text == "🛑 Stop Space":
        await stop_command(update, context)
        return
    elif text in ("⚡ Keep Awake", "⚡ Awake"):
        await awake_command(update, context)
        return
    elif text == "📊 Status":
        await status_command(update, context)
        return

    # Handle input following a button prompt
    current_action = user_state.get(user_id)
    if current_action == "waiting_for_like_url":
        user_state[user_id] = None
        tweet_url = text.split()[0]
        tokens = bot_engine.get_tokens()
        if not tokens:
            await update.message.reply_text(
                "❌ *No accounts found!*\n\n"
                "• On your PC: Make sure `tokens.txt` has your tokens.\n"
                "• On Render: Go to Environment Variables and add `X_TOKENS` with your tokens.",
                parse_mode="Markdown"
            )
            return
        asyncio.create_task(run_engagement_task(update.effective_chat.id, context.bot, mode=1, target_url=tweet_url))
        return

    elif current_action == "waiting_for_comment_url":
        user_state[user_id] = None
        parts = text.split(maxsplit=1)
        tweet_url = parts[0]
        custom_comment = parts[1] if len(parts) > 1 else None
        tokens = bot_engine.get_tokens()
        if not tokens:
            await update.message.reply_text(
                "❌ *No accounts found!*\n\n"
                "• On your PC: Make sure `tokens.txt` has your tokens.\n"
                "• On Render: Go to Environment Variables and add `X_TOKENS` with your tokens.",
                parse_mode="Markdown"
            )
            return
        asyncio.create_task(run_engagement_task(update.effective_chat.id, context.bot, mode=2, target_url=tweet_url, custom_comment=custom_comment))
        return

    elif current_action == "waiting_for_space_url":
        user_state[user_id] = None
        space_url = text.split()[0]
        global current_space_task
        if current_space_task and not current_space_task.done():
            await update.message.reply_text("⚠️ A Space session is already running! Tap `🛑 Stop Space` first.", parse_mode="Markdown")
            return
        current_space_task = asyncio.create_task(run_space_session(update.effective_chat.id, context.bot, space_url))
        return

    # Fallback response with keyboard
    await update.message.reply_text("👇 Choose an action below or send a command:", reply_markup=get_main_keyboard())

def main():
    cfg = load_config()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or cfg.get("telegram_bot_token", "").strip()

    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("\n" + "=" * 65)
        print(" [!] TELEGRAM BOT TOKEN REQUIRED")
        print("=" * 65)
        print(" 1. Open Telegram and search for @BotFather")
        print(" 2. Send '/newbot' and choose a name and username for your bot")
        print(" 3. Copy the HTTP API token BotFather gives you")
        print(" 4. Paste it into 'telegram_config.json' or set TELEGRAM_BOT_TOKEN env variable!")
        print("=" * 65 + "\n")
        token_input = input("Or paste your Telegram Bot Token here now: ").strip()
        if token_input:
            cfg["telegram_bot_token"] = token_input
            save_config(cfg)
            token = token_input
        else:
            print("[-] Exiting. Please configure telegram_config.json.")
            return

    print("=" * 65)
    print("      TELEGRAM BOT CONTROLLER IS RUNNING ONLINE")
    print("      Open Telegram and send /start to your bot!")
    print("=" * 65)

    app = ApplicationBuilder().token(token).post_init(start_web_server).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("like", like_command))
    app.add_handler(CommandHandler("comment", comment_command))
    app.add_handler(CommandHandler("space", space_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("awake", awake_command))

    # Message handler for keyboard buttons and conversational inputs
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_or_text))

    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] Telegram bot stopped.")
