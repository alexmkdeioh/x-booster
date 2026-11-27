# X (Twitter) Multi-Account Automation & Presence Suite

A lightweight, multi-account automation engine for Twitter/X to:
1. **Like any Tweet**
2. **Like & Comment on any Tweet**
3. **Space Listener (Boost & Maintain Presence)**
4. **Space Listener + Like & Comment**
5. **📱 Remote Control from anywhere in the world via Telegram Bot!**

---

## 📁 Project Structure

```
x_space_booster_project/
│
├── start_telegram_bot.bat          <- Run to control bots from your phone anywhere!
├── start_telegram_bot.command      <- Mac version for Telegram remote controller
├── telegram_bot.py                 <- Telegram bot server
├── telegram_config.json            <- Telegram bot token & whitelist
│
├── start_listeners.bat             <- Windows desktop launcher (interactive menu)
├── start_listeners.command         <- Mac desktop launcher
├── space_listener_browser_bot.py   <- Headless automation engine
├── tokens.txt                      <- Paste your auth_tokens here (one per line)
├── comments.txt                    <- Put custom comments here (one per line)
│
└── x_token_extractor_extension/    <- Chrome/Brave browser extension
```

---

## 📱 Option 1: Remote Control from Anywhere via Telegram

### Step 1: Create your free Telegram Bot (Takes 1 minute)
1. Open Telegram on your phone or PC and search for **`@BotFather`**.
2. Send the message `/newbot`.
3. Choose a name (e.g. `My X Booster`) and a username ending in `bot` (e.g. `my_x_booster_bot`).
4. `@BotFather` will give you a token like `123456789:ABCdefGhIJKlmNo...`.

### Step 2: Add your Bot Token
Open [telegram_config.json](file:///c:/Users/mahab/Documents/antigravity/x_space_booster_project/telegram_config.json) and paste your token:
```json
{
  "telegram_bot_token": "YOUR_TOKEN_HERE",
  "allowed_user_ids": []
}
```

### Step 3: Start the Bot
- Double-click **`start_telegram_bot.bat`** (or run `python telegram_bot.py`).

### Step 4: Control from Your Phone Anywhere!
Open Telegram, message your bot, and send:
- `/start` - Shows the control panel and binds securely to your account.
- `/like https://x.com/username/status/123456789` - Likes the tweet with all accounts and sends you photo proof!
- `/comment https://x.com/username/status/123456789 Great post! 🔥` - Likes and comments on the tweet.
- `/space https://x.com/i/spaces/1XXXXXX` - Joins a Space and keeps presence.
- `/stop` - Stops active Space listeners.
- `/status` - Checks online status and loaded accounts.

---

## ☁️ Running 24/7 on the Cloud (VPS)

To run this without keeping your personal computer turned on:
1. Rent a cheap cloud VPS (DigitalOcean $4/mo, Hetzner €3/mo, AWS Free Tier, or Oracle Cloud Free Tier).
2. Copy this folder to the server.
3. Run `python3 -m pip install playwright python-telegram-bot && python3 -m playwright install --with-deps chromium`.
4. Start the bot with `nohup python3 telegram_bot.py &` or `pm2 start telegram_bot.py`.
5. Now you can trigger likes, comments, and space joins straight from your phone wherever you are!
