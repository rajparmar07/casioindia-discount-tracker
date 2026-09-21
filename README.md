# ⌚ Casio India Real-Time Discount Tracker

A lightweight, automated alert bot that continuously monitors [Casio India (casiostore.bhawar.com)](https://casiostore.bhawar.com/collections/watches) for random price drops and discounts, sending instant notifications directly to your **Telegram** account with product photo, discount percentage, savings, and a direct 1-click buy link.

---

## ✨ Features
- **Real-Time Shopify API Feeds**: Directly queries Shopify's JSON endpoint (`/collections/watches/products.json`) without brittle HTML scraping or headless browsers.
- **Instant Telegram Alerts**: Sends rich alerts containing:
  - ⌚ Watch Name & Model
  - 🏷️ Discount % (e.g., `30% OFF`, `50% OFF`)
  - 💰 Deal Price vs MRP & Exact Savings (in ₹)
  - 📦 In-Stock verification (filters out out-of-stock ghost sales)
  - 🔗 Direct Buy Now button & watch image preview
- **Duplicate Suppression**: Keeps a persistent state in `data/state.json` so you are never spammed with repeat alerts for the same deal.
- **Smart Detection**: Detects:
  - Brand-new discounts
  - Further price reductions (e.g., drops from 20% to 40%)
  - Restocks on already discounted watches
- **Flexible Deployment**:
  - **Local**: Run on your Windows/Mac/Linux PC.
  - **24/7 Free Cloud**: Run seamlessly via **GitHub Actions** (included) or **Render / Koyeb**.

---

## 🚀 Quick Start (Local Setup)

### Step 1: Create your Telegram Bot (2 minutes)
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, name your bot (e.g. `Casio Alert Bot`), and choose a username ending in `bot` (e.g. `my_casio_deals_bot`).
3. Copy the **HTTP API Token** provided by BotFather.
4. Next, search for [@userinfobot](https://t.me/userinfobot) on Telegram, click **Start**, and note your numeric **Id** (this is your `CHAT_ID`).
5. Open your newly created bot in Telegram and click **Start** (important: bots cannot message you first until you start the conversation).

### Step 2: Configure Environment
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Open `.env` and fill in your details:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
MIN_DISCOUNT_PERCENT=1
CHECK_INTERVAL_SECONDS=120
```

### Step 3: Install Requirements
```bash
pip install -r requirements.txt
```

### Step 4: Test Telegram Connection
```bash
python casio_tracker.py --test-telegram
```
You should instantly receive a sample watch alert on your Telegram!

### Step 5: Run the Tracker
```bash
# Continuous 24/7 loop (checks every 120 seconds):
python casio_tracker.py

# Or run a single scan and exit:
python casio_tracker.py --once

# Or test without sending messages:
python casio_tracker.py --dry-run
```

---

## ☁️ 24/7 Free Cloud Hosting with GitHub Actions

You can host this 100% free on GitHub without keeping your computer on:

1. **Push this project to a new GitHub repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Casio discount tracker"
   git branch -M main
   git remote add origin https://github.com/rajparmar07/casioindia-discount-tracker.git
   git push -u origin main
   ```
2. **Add Telegram Secrets to GitHub**:
   - Go to your repository on GitHub.
   - Click **Settings** $
ightarrow$ **Secrets and variables** $
ightarrow$ **Actions**.
   - Click **New repository secret**:
     - Name: `TELEGRAM_BOT_TOKEN`, Value: `<Your Telegram Bot Token>`
     - Name: `TELEGRAM_CHAT_ID`, Value: `<Your Numeric Telegram Chat ID>`
3. **Ensure Workflow Permissions**:
   - In your repo: **Settings** $
ightarrow$ **Actions** $
ightarrow$ **General**.
   - Under **Workflow permissions**, select **Read and write permissions** (this allows the bot to commit `data/state.json` back to prevent duplicate alerts).
   - Click **Save**.
4. **Done!** The workflow in `.github/workflows/tracker.yml` will automatically run every 10 minutes 24/7 and alert your Telegram instantly whenever a new discount drops.

---

## ⚙️ CLI Options Reference

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--once` | Run a single scan and exit | `False` (continuous) |
| `--interval <sec>` | Seconds between checks in continuous mode | `120` |
| `--min-discount <pct>` | Only alert if discount is at least this percentage | `1.0` |
| `--dry-run` | Scan and display findings in console without sending alerts | `False` |
| `--test-telegram` | Send a verification test alert to Telegram | - |
| `--all-products` | Monitor the entire catalog (~1,350 items) instead of just watches (~470 items) | `False` |
| `--reset-state` | Clear stored price history and start fresh | - |
