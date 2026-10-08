# 🎁 John's Giveaway Bot • AI-Powered Community Growth Platform

A professional, production-ready Telegram Giveaway Platform built with Python 3.13, **aiogram 3**, **Groq AI**, **Pillow HD Poster Studio**, and **SQLAlchemy 2.0 (Async)**. Featuring a modern, high-conversion UI, real-time channel membership verification, viral referral tracking, automated cryptographic winner selection, live roulette draw animation, secret promo vouchers, community leaderboards, and an in-bot admin control panel.

---

## 🌟 Key Highlights & Advanced Features

### 🤖 Groq AI Intelligence (`llama-3.3-70b-versatile`)
- **AI Concierge for Users:** Real-time interactive Q&A (`/ask <question>` or via the inline menu) answering user questions about rules, referral multipliers, prize delivery, and fairness.
- **AI Copywriter for Admins:** 1-click viral giveaway announcement generator creating persuasive, high-converting copy with emojis and urgency.

### 🎨 HD Poster Studio & Live Animations
- **Dynamic Graphical Poster Generator:** Uses Pillow to render 1000x560 HD promotional banner graphics on-the-fly for any giveaway.
- **Live Slot Roulette Draw Animation:** Simulates a thrilling live lottery reveal (`🎰 Drawing... [ 🎲 🎲 🎲 ] ➔ [ 🍒 7 🔔 ] ➔ [ 💎 💎 💎 ]`) before revealing winners.

### 🏆 Gamification & Community Growth
- **Community Leaderboard:** Live Hall of Fame ranking top referrers and top ticket holders with gold/silver/bronze medals.
- **Secret Promo / Voucher Codes:** Admins can drop limited promo codes (`/redeem <code>`) for instant bonus entries.
- **Daily Bonus:** Free entry claimable every 24 hours.

### ⚙️ Administration Dashboard
- **In-Bot Admin Panel (`/admin`):**
  - **Create Giveaway Wizard (FSM):** Step-by-step creation of Title, Description, Prize, Winners count, Duration (`24h`, `3d`, or UTC timestamps), Referral Bonus, and Max Entries cap.
  - **Giveaway Control:** Real-time metrics, pause/resume, delete, manual winner draw, and broadcast announcement with interactive [Join] button.
  - **Mandatory Channel Manager:** Add/remove channels requiring membership verification.
  - **Broadcast Engine:** High-throughput rate-limited messaging (~25 msgs/sec) to prevent Telegram API 429 flood errors, tracking sent, blocked, and failed counts.
  - **Winner Claims Manager:** One-tap [Approve], [Reject], or [Request Info] actions with automatic winner notifications.
  - **Anti-Cheat & Ban System:** Instant `/ban <user_id> [reason]` and `/unban <user_id>` with middleware-level enforcement.
  - **Live Platform Analytics:** Real-time SQL aggregations for total users, active giveaways, total entries, valid referrals, and winners crowned.

### 🛡️ Anti-Abuse Protections
- **User ID Primary Identity:** Rejection of spoofed usernames; all transactions tied directly to Telegram 64-bit integer IDs.
- **Anti-Self-Referral:** Users cannot refer themselves.
- **Anti-Duplicate-Referral:** Permanent binding to the first inviter; cannot be manipulated by rejoining via other links.
- **Conditional Referral Reward:** Referrers are **only credited** after the referred user joins an active giveaway and verifies channel membership.
- **Throttling Middleware:** In-memory anti-spam and flood protection.
- **Ban Enforcement Middleware:** Instantly drops queries and alerts banned accounts.

---

## 📁 Project Architecture

```
telegram_giveaway_bot/
├── bot.py                     # Application entry point, polling, middleware setup
├── config.py                  # Pydantic Settings & environment variable parsing
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container image specification
├── docker-compose.yml         # Container stack with PostgreSQL
├── .env.example               # Environment variables template
├── README.md                  # Complete documentation and setup manual
│
├── database/
│   ├── __init__.py
│   ├── database.py            # Async engine, sessionmaker, schema initialization
│   ├── models.py              # SQLAlchemy 2.0 async models
│   └── repositories.py        # High-performance async repositories
│
├── handlers/
│   ├── __init__.py            # Router registration
│   ├── start.py               # /start, onboarding, and referral parameter parsing
│   ├── giveaways.py           # Browsing, channel verification, joining, daily bonus
│   ├── referrals.py           # Referral stats and viral share link
│   ├── profile.py             # User profile and ticket breakdown
│   ├── winners.py             # Public winners archive & audit hashes
│   ├── claims.py              # Winner prize claim FSM and admin review
│   └── admin.py               # Complete admin dashboard, wizards, and controls
│
├── services/
│   ├── __init__.py
│   ├── giveaway_service.py    # Participation logic, daily bonus, profile aggregates
│   ├── verification_service.py# Telegram Bot API get_chat_member verification
│   ├── referral_service.py    # Referral binding, validation, and reward qualification
│   ├── winner_service.py      # Auditable weighted random draw algorithm
│   ├── notification_service.py# Direct message delivery to winners and referrers
│   └── broadcast_service.py   # Rate-limited broadcasting engine
│
├── keyboards/
│   ├── __init__.py
│   ├── user.py                # User menus, paginated giveaway buttons, verification
│   └── admin.py               # Admin control keyboards, claim reviews, channel actions
│
├── middlewares/
│   ├── __init__.py
│   ├── ban.py                 # Suspension enforcement middleware
│   └── throttling.py          # Anti-flood rate limiting middleware
│
├── utils/
│   ├── __init__.py
│   ├── formatting.py          # Visual styling for cards, medals, and countdowns
│   ├── validators.py          # Duration, date, and chat identifier parsers
│   └── scheduler.py           # Continuous background worker for giveaway expiration
│
└── tests/
    ├── conftest.py            # In-memory async SQLite engine & mock Bot fixtures
    ├── test_ban_security.py   # Ban/unban and admin permission checks
    ├── test_claims.py         # Claim flow and review state transitions
    ├── test_giveaways.py      # Verification, joining, caps, and daily bonus
    ├── test_users_referrals.py# User registration, self-referral, referral reward
    ├── test_winner_selection.py# Weighted random draw & cryptographic audit hash
    └── test_scheduler_and_edge_cases.py # Expired giveaway auto-draw and broadcasts
```

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.11, 3.12, or 3.13
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Your Telegram User ID from [@userinfobot](https://t.me/userinfobot)

### 2. Clone and Setup Environment

```bash
# Clone or navigate to the directory
cd telegram_giveaway_bot

# Create and activate a Python virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Configure `.env`
Copy the example file and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
BOT_USERNAME=YourBotUsernameWithoutAt
ADMIN_IDS=123456789
DATABASE_URL=sqlite+aiosqlite:///giveaway_bot.db
```

### 4. Run the Bot
```bash
python bot.py
```

The database tables are automatically initialized on startup. The background scheduler starts immediately.

---

## 🧪 Running Automated Tests

Run the full async test suite using `pytest`:

```bash
pytest tests/ -v
```

All 20 tests execute against an isolated in-memory SQLite database in seconds.

---

## 🌐 Production Deployment Guides

### A. Deploy on Render
1. Create a new repository on GitHub and push the codebase.
2. Sign in to [Render](https://render.com).
3. **Add PostgreSQL:**
   - Click **New +** -> **PostgreSQL**.
   - Create the database and copy the **Internal Database URL** (e.g. `postgresql://user:pass@host/db`).
4. **Deploy Background Worker / Web Service:**
   - Click **New +** -> **Background Worker** (or Web Service).
   - Connect your GitHub repository.
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. **Set Environment Variables on Render:**
   - `BOT_TOKEN`: `Your bot token`
   - `BOT_USERNAME`: `Your bot username`
   - `ADMIN_IDS`: `Your Telegram user ID`
   - `DATABASE_URL`: `postgresql+asyncpg://user:pass@host/db` *(make sure to prefix with postgresql+asyncpg)*
6. Click **Deploy**.

---

### B. Deploy on Railway
1. Sign in to [Railway](https://railway.app).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Add a **PostgreSQL** plugin from Railway:
   - Click **+ New** -> **Database** -> **Add PostgreSQL**.
4. Link the database to your service:
   - In your bot service **Variables**, Railway automatically provides `DATABASE_URL`.
   - Add the asyncpg driver prefix: change `postgresql://` to `postgresql+asyncpg://${{Postgres.DATABASE_URL}}` or override with the full connection string.
5. Set `BOT_TOKEN`, `BOT_USERNAME`, and `ADMIN_IDS`.
6. Railway will automatically build via `Dockerfile` or `requirements.txt` and launch `python bot.py`.

---

### C. Deploy on a VPS (Linux / Ubuntu)

```bash
# Update system
sudo apt update && sudo apt install -y python3-pip python3-venv git

# Clone repository
git clone <repo-url> /opt/giveaway_bot
cd /opt/giveaway_bot

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env

# Create Systemd Service
sudo nano /etc/systemd/system/giveaway_bot.service
```

Add the following configuration:
```ini
[Unit]
Description=Telegram Giveaway Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/giveaway_bot
ExecStart=/opt/giveaway_bot/venv/bin/python /opt/giveaway_bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable giveaway_bot
sudo systemctl start giveaway_bot
sudo systemctl status giveaway_bot
```

---

### D. Deploy with Docker Compose

Ensure Docker and Docker Compose are installed, then run:

```bash
# Edit .env with your BOT_TOKEN and ADMIN_IDS
cp .env.example .env
nano .env

# Build and start services (Bot + PostgreSQL) in detached mode
docker compose up -d --build

# View real-time logs
docker compose logs -f bot
```

---

## 📖 Admin & User Operations Manual

### Admin Operations
1. Open your bot in Telegram and send `/admin`.
2. **Creating a Giveaway:**
   - Tap **🎁 Create Giveaway** (or run `/create`).
   - Follow the wizard: Title ➔ Description ➔ Prize ➔ Winners Count ➔ Duration (e.g. `24h` or `3d`) ➔ Referral Bonus ➔ Max Entries ➔ Rules.
   - Tap **📢 Announce to Users** inside the giveaway view to broadcast an attractive card with a [Join] button to all registered users.
3. **Mandatory Channel Verification:**
   - Add your bot as an **Administrator** in your Telegram channels/groups.
   - Go to `/admin` ➔ **📣 Required Channels** ➔ **➕ Add New Channel**.
   - Provide `@channelusername` and a title. The bot will now verify that every user is an active member before granting giveaway entries!
4. **Drawing Winners:**
   - The bot automatically closes expired giveaways and selects winners every 30 seconds via the background scheduler.
   - You can also manually draw winners at any time by selecting the giveaway in `/admin` and clicking **🏆 Draw Winners Now**.
5. **Processing Prize Claims:**
   - Winners receive a private alert with a **🎁 CLAIM PRIZE** button.
   - When a winner submits their details, all admins receive an instant alert with action buttons:
     - `✅ Approve Claim` ➔ Marks approved and notifies winner.
     - `❌ Reject Claim` ➔ Marks rejected and alerts winner.
     - `🔄 Request Details` ➔ Asks for clarification.
6. **Broadcasting Updates:**
   - Send `/broadcast` or tap **📢 Broadcast**.
   - Send any text or photo. Review target recipient count and tap **🚀 CONFIRM & SEND**.
7. **User Moderation:**
   - Ban suspected cheaters: `/ban 123456789 Suspicious multi-account`
   - Unban: `/unban 123456789`

### User Operations
1. Send `/start` to view the **GIVEAWAY HUB** menu.
2. Tap **🎁 Active Giveaways** to view available contests.
3. Tap **🎟 JOIN GIVEAWAY NOW**. The bot checks membership across all required channels. If you have not joined yet, it presents links and a **🔄 Verify Again** button.
4. Tap **👥 Refer & Earn** to copy your unique referral link: `https://t.me/YourBot?start=ref_123456`. When friends join through your link and participate, you receive extra bonus tickets!
5. Tap **🔥 Daily Bonus (+1)** once every 24 hours to earn free extra tickets.
6. Tap **👤 My Profile** to view total entries, valid referrals, and won giveaways.
7. Concluded giveaways and official winners can be verified anytime in **🏆 Winners**.
