# ⌚ Casio India Real-Time Deals, Restocks & New Arrivals Tracker

[![Casio Discount Monitor](https://github.com/rajparmar07/casioindia-discount-tracker/actions/workflows/tracker.yml/badge.svg)](https://github.com/rajparmar07/casioindia-discount-tracker/actions)

A high-performance automated monitor that watches [Casio India (casiostore.bhawar.com)](https://casiostore.bhawar.com/collections/watches) 24/7 and sends instant, high-converting notification cards to your **Telegram Channel** with product photos, discount percentages, savings callouts, and 1-click buy buttons.

---

## ⚡ Real-Time Alert Scenarios

The bot automatically identifies and formats 5 distinct scenarios:

| Scenario | Trigger Condition | Telegram Format |
| :--- | :--- | :--- |
| **✨ Fresh Drop / New Arrival** | Watch newly listed on Casio store catalog | *"✨ JUST DROPPED ON CASIO INDIA!"* + `🛍️ Grab New Arrival ➔` |
| **🚨 Back in Stock** | Previously sold-out watch is now back in stock | *"🚨 BACK IN STOCK ALERT!"* + `⚡ Buy Before It Sells Out ➔` |
| **🚨💥 Restocked on Sale** | Discounted watch returns to stock | *"🚨💥 RESTOCKED & ON SALE!"* + `🔥 Claim Deal Now ➔` |
| **🚨🔥 New Discount** | Watch price slashed with a fresh discount | *"🚨🔥 DISCOUNT JUST DROPPED!"* + `🛒 Buy Now (Save ₹X) ➔` |
| **⚡⚡ Price Drop** | Already discounted watch drops even lower | *"⚡⚡ PRICE DROP: EVEN CHEAPER!"* + `💥 Snatch Lowest Price ➔` |

---

## 🚀 Quick Start (Local Setup)

### Step 1: Configure Environment
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Fill in your credentials:
```env
TELEGRAM_BOT_TOKEN=8895386525:AAG23va6eZ_wvZ-O2KlOm_R0QT8W4Et_fOc
TELEGRAM_CHAT_ID=-1004370492757
NOTIFY_NEW_LISTINGS=true
NOTIFY_RESTOCKS=true
NOTIFY_DISCOUNTS=true
```

### Step 2: Install Requirements
```bash
pip install -r requirements.txt
```

### Step 3: Preview the 5 Catchy Templates in Telegram
```bash
python casio_tracker.py --test-templates
```
This instantly sends a live preview of all 5 formatted cards directly into your Telegram channel!

### Step 4: Run the Tracker
```bash
# Run continuous loop locally:
python casio_tracker.py

# Or run single scan and exit:
python casio_tracker.py --once

# Or test without sending alerts:
python casio_tracker.py --dry-run
```

---

## ☁️ 24/7 Automated Hosting (GitHub Actions & cron-job.org)

1. **GitHub Actions**: The workflow in `.github/workflows/tracker.yml` runs automatically in the background.
2. **cron-job.org Trigger**: Triggers GitHub Actions on the exact minute without delay using the GitHub Workflow Dispatch API.
3. **1-Click Reset in GitHub UI**:
   - In the **Actions** tab $ightarrow$ **Casio Discount Monitor** $ightarrow$ **Run workflow**.
   - Tick the checkbox: ☑️ **Reset state cache (re-send all currently active discount alerts)?** to clear state and re-broadcast current deals.

---

## ⚙️ CLI Reference

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--once` | Run a single scan and exit | `False` |
| `--test-templates` | Send all 5 catchy preview cards to Telegram | - |
| `--dry-run` | Scan store and print findings without sending alerts | `False` |
| `--min-discount <pct>` | Minimum discount percentage to trigger discount alerts | `1.0` |
| `--all-products` | Scan all ~1,350 store products instead of ~470 watches | `False` |
| `--reset-state` | Clear stored state database before running | - |
| `--notify-all-new` | If state is empty, alert for all items instead of baseline seeding | `False` |
