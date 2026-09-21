#!/usr/bin/env python3
"""
Casio India Real-Time Discount Tracker (Telegram Bot)
Monitors casiostore.bhawar.com for discounts and instant price drops.
"""

import os
import sys
import time
import json
import logging
import argparse
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://casiostore.bhawar.com"
WATCHES_URL = f"{BASE_URL}/collections/watches/products.json?limit=250&page={{}}"
ALL_URL = f"{BASE_URL}/products.json?limit=250&page={{}}"
DEFAULT_STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "state.json")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def load_state(filepath: str) -> Dict[str, Any]:
    """Load existing price tracking state from disk."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load state file ({e}). Starting with empty state.")
        return {}


def save_state(filepath: str, state: Dict[str, Any]) -> None:
    """Persist state to disk safely using atomic write."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    temp_path = f"{filepath}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(temp_path, filepath)


def fetch_json(url: str, retries: int = 3, delay: float = 2.0) -> Optional[Dict[str, Any]]:
    """Fetch JSON from a URL with retries and realistic headers."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status == 200:
                    data = resp.read().decode("utf-8")
                    return json.loads(data)
        except Exception as e:
            logger.warning(f"Fetch attempt {attempt}/{retries} failed for {url}: {e}")
            if attempt < retries:
                time.sleep(delay * attempt)
    return None


def get_all_products(scan_all: bool = False) -> List[Dict[str, Any]]:
    """Fetch all watch products from Shopify JSON endpoint."""
    endpoint_template = ALL_URL if scan_all else WATCHES_URL
    all_products = []
    page = 1
    max_pages = 20

    while page <= max_pages:
        url = endpoint_template.format(page)
        data = fetch_json(url)
        if not data or "products" not in data:
            break
        products = data["products"]
        if not products:
            break
        all_products.extend(products)
        page += 1
        time.sleep(0.3)  # Polite request pacing

    logger.info(f"Fetched {len(all_products)} products across {page - 1} pages.")
    return all_products


def send_telegram_alert(
    bot_token: str,
    chat_id: str,
    title: str,
    price: float,
    compare_at: float,
    discount_pct: float,
    savings: float,
    url: str,
    image_url: Optional[str] = None,
    alert_type: str = "NEW_DISCOUNT"
) -> bool:
    """Send formatted rich notification to one or multiple Telegram chat/channel IDs."""
    if not bot_token or not chat_id:
        logger.error("Telegram Bot Token or Chat ID not configured!")
        return False

    targets = [c.strip() for c in str(chat_id).split(",") if c.strip()]
    if not targets:
        return False

    if alert_type == "RESTOCK":
        header = "🎉 <b>RESTOCKED ON DISCOUNT!</b>"
    elif alert_type == "PRICE_DROP":
        header = "⚡ <b>FURTHER PRICE DROP!</b>"
    else:
        header = "🔥 <b>NEW CASIO DISCOUNT!</b>"

    caption = (
        f"{header}\n\n"
        f"⌚ <b>{title}</b>\n"
        f"🏷 <b>Discount:</b> <b>{discount_pct}% OFF</b>\n"
        f"💰 <b>Deal Price:</b> ₹{price:,.2f}  <s>₹{compare_at:,.2f}</s>\n"
        f"💵 <b>You Save:</b> ₹{savings:,.2f}\n"
        f"📦 <b>Stock:</b> In Stock ✅\n\n"
        f'🔗 <a href="{url}">👉 View Watch on Casio Store</a>'
    )

    reply_markup = {
        "inline_keyboard": [
            [{"text": "🛒 Open Product Page", "url": url}]
        ]
    }

    all_success = True
    for target_id in targets:
        sent = False
        # Try photo first if available
        if image_url:
            send_photo_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            payload = {
                "chat_id": target_id,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": reply_markup
            }
            try:
                req = urllib.request.Request(
                    send_photo_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        logger.info(f"Telegram photo alert sent to {target_id}: {title}")
                        sent = True
            except Exception as e:
                logger.warning(f"Failed to send photo to {target_id} ({e}), trying text message...")

        if not sent:
            send_msg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": target_id,
                "text": caption,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
                "reply_markup": reply_markup
            }
            try:
                req = urllib.request.Request(
                    send_msg_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        logger.info(f"Telegram text alert sent to {target_id}: {title}")
                        sent = True
            except Exception as e:
                logger.error(f"Failed to send Telegram message to {target_id}: {e}")
                all_success = False

    return all_success


def run_scan(
    bot_token: str,
    chat_id: str,
    state_file: str,
    min_discount: float,
    scan_all: bool,
    dry_run: bool = False
) -> int:
    """Scan product catalog and trigger alerts for new discounts or price drops."""
    state = load_state(state_file)
    products = get_all_products(scan_all=scan_all)
    alerts_triggered = 0

    for product in products:
        handle = product.get("handle", "")
        product_url = f"{BASE_URL}/products/{handle}"
        product_title = product.get("title", "Casio Watch")
        images = product.get("images", [])
        image_url = images[0].get("src") if images else None

        for variant in product.get("variants", []):
            var_id = str(variant.get("id", ""))
            key = f"{product.get('id')}_{var_id}"
            is_available = bool(variant.get("available", False))

            try:
                price = float(variant.get("price") or 0)
                compare_at = float(variant.get("compare_at_price") or 0)
            except (ValueError, TypeError):
                continue

            has_discount = compare_at > price and price > 0
            if not has_discount:
                # Update current non-discounted price quietly
                state[key] = {
                    "title": product_title,
                    "price": price,
                    "compare_at": compare_at,
                    "discount_pct": 0,
                    "available": is_available,
                    "updated_at": time.time()
                }
                continue

            discount_pct = round(((compare_at - price) / compare_at) * 100, 1)
            savings = round(compare_at - price, 2)

            if discount_pct < min_discount:
                continue

            prev_record = state.get(key)
            trigger_alert = False
            alert_type = "NEW_DISCOUNT"

            if not prev_record:
                if is_available:
                    trigger_alert = True
                    alert_type = "NEW_DISCOUNT"
            else:
                prev_price = prev_record.get("price", price)
                prev_discount = prev_record.get("discount_pct", 0)
                prev_available = prev_record.get("available", False)

                # Event 1: Price dropped even lower
                if price < prev_price and is_available:
                    trigger_alert = True
                    alert_type = "PRICE_DROP"
                # Event 2: Previously out of stock while discounted, now back in stock!
                elif is_available and not prev_available and prev_discount > 0:
                    trigger_alert = True
                    alert_type = "RESTOCK"
                # Event 3: Previously recorded without discount, now discounted
                elif is_available and prev_discount == 0:
                    trigger_alert = True
                    alert_type = "NEW_DISCOUNT"

            state[key] = {
                "title": product_title,
                "price": price,
                "compare_at": compare_at,
                "discount_pct": discount_pct,
                "available": is_available,
                "updated_at": time.time()
            }

            if trigger_alert:
                alerts_triggered += 1
                logger.info(
                    f"[{alert_type}] {product_title} | ₹{price:,.2f} ({discount_pct}% OFF, MRP ₹{compare_at:,.2f})"
                )
                if dry_run:
                    logger.info("  -> [DRY-RUN] Telegram alert skipped.")
                else:
                    send_telegram_alert(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        title=product_title,
                        price=price,
                        compare_at=compare_at,
                        discount_pct=discount_pct,
                        savings=savings,
                        url=product_url,
                        image_url=image_url,
                        alert_type=alert_type
                    )
                    time.sleep(1.0)

    if not dry_run:
        save_state(state_file, state)
        logger.info(f"State saved ({len(state)} variants tracked). Alerts sent: {alerts_triggered}")
    else:
        logger.info(f"Dry run complete. Potential alerts detected: {alerts_triggered}")

    return alerts_triggered


def test_telegram_connection(bot_token: str, chat_id: str) -> None:
    """Send a sample test notification to verify Telegram setup."""
    logger.info("Sending test alert to Telegram...")
    success = send_telegram_alert(
        bot_token=bot_token,
        chat_id=chat_id,
        title="Casio G-Shock Test Watch (GA-B2100)",
        price=7995.0,
        compare_at=11995.0,
        discount_pct=33.3,
        savings=4000.0,
        url=f"{BASE_URL}/collections/watches",
        image_url="https://cdn.shopify.com/s/files/1/0910/0073/3977/files/GA-2100RL-1A.png",
        alert_type="NEW_DISCOUNT"
    )
    if success:
        logger.info("Test alert successfully delivered! Your Telegram bot is active and working.")
    else:
        logger.error("Failed to send test alert. Please verify your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")


def main():
    parser = argparse.ArgumentParser(description="Real-Time Casio India Discount Alert Bot")
    parser.add_argument("--once", action="store_true", help="Run a single scan and exit (for GitHub Actions / Cron)")
    parser.add_argument("--interval", type=int, default=None, help="Polling interval in seconds (default: from .env or 120)")
    parser.add_argument("--min-discount", type=float, default=None, help="Minimum discount percentage to trigger alert (e.g. 10 for 10 percent)")
    parser.add_argument("--dry-run", action="store_true", help="Scan without sending Telegram notifications or updating state")
    parser.add_argument("--test-telegram", action="store_true", help="Send a test message to Telegram and exit")
    parser.add_argument("--all-products", action="store_true", help="Scan all store products instead of just /collections/watches")
    parser.add_argument("--state-file", type=str, default=DEFAULT_STATE_FILE, help="Path to state.json")
    parser.add_argument("--reset-state", action="store_true", help="Clear stored state file before running")

    args = parser.parse_args()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    min_discount = args.min_discount
    if min_discount is None:
        try:
            min_discount = float(os.getenv("MIN_DISCOUNT_PERCENT", "1.0"))
        except ValueError:
            min_discount = 1.0

    scan_all = args.all_products or os.getenv("SCAN_ALL_PRODUCTS", "false").lower() == "true"

    interval = args.interval
    if interval is None:
        try:
            interval = int(os.getenv("CHECK_INTERVAL_SECONDS", "120"))
        except ValueError:
            interval = 120

    if args.reset_state and os.path.exists(args.state_file):
        os.remove(args.state_file)
        logger.info(f"Reset state file: {args.state_file}")

    if args.test_telegram:
        if not bot_token or not chat_id:
            logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment or .env file.")
            sys.exit(1)
        test_telegram_connection(bot_token, chat_id)
        return

    if not args.dry_run and (not bot_token or not chat_id):
        logger.warning(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured! "
            "Falling back to DRY-RUN mode. Set credentials in .env for live alerts."
        )
        args.dry_run = True

    mode_name = "Single Run (--once)" if args.once else f"Continuous Loop (Every {interval}s)"
    scope_name = "All Store Products" if scan_all else "Watches Collection"
    logger.info("=" * 60)
    logger.info("Casio India Watch Discount Tracker")
    logger.info(f"Scope: {scope_name}")
    logger.info(f"Min Discount Threshold: {min_discount}%")
    logger.info(f"Mode: {mode_name}")
    logger.info(f"Dry Run: {args.dry_run}")
    logger.info("=" * 60)

    if args.once:
        run_scan(bot_token, chat_id, args.state_file, min_discount, scan_all, dry_run=args.dry_run)
    else:
        while True:
            try:
                run_scan(bot_token, chat_id, args.state_file, min_discount, scan_all, dry_run=args.dry_run)
            except Exception as e:
                logger.error(f"Unexpected error during scan: {e}", exc_info=True)
            logger.info(f"Sleeping for {interval} seconds until next check...")
            time.sleep(interval)


if __name__ == "__main__":
    main()
