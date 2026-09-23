#!/usr/bin/env python3
"""
Casio India Real-Time Deal, Restock & New Listing Tracker (Telegram Bot)
Monitors casiostore.bhawar.com for new arrivals, inventory restocks, and price drops.
"""

import os
import sys
import time
import json
import logging
import argparse
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple

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
        time.sleep(0.3)

    logger.info(f"Fetched {len(all_products)} products across {page - 1} pages.")
    return all_products


def format_catchy_alert(
    alert_type: str,
    title: str,
    price: float,
    compare_at: float,
    discount_pct: float,
    savings: float,
    url: str
) -> Tuple[str, Dict[str, Any]]:
    """Generate high-converting, catchy Telegram message cards with custom buttons for each scenario.
    Always includes discount percentage, deal price vs MRP, and savings for ANY scenario if a discount exists.
    """
    has_discount = discount_pct > 0 and compare_at > price and savings > 0

    # Build the pricing block dynamically based on whether discount exists
    if has_discount:
        price_block = (
            f"🏷️ <b>Discount:</b> <b>💥 {discount_pct}% OFF!</b>\n"
            f"💰 <b>Deal Price:</b> <b>₹{price:,.2f}</b>  <s>₹{compare_at:,.2f}</s>\n"
            f"💵 <b>You Save:</b> <b>₹{savings:,.2f} OFF MRP!</b>"
        )
    else:
        price_block = f"💰 <b>Price:</b> <b>₹{price:,.2f}</b> (MRP)"

    if alert_type == "NEW_LISTING":
        if has_discount:
            header = f"✨ <b>JUST DROPPED WITH {discount_pct}% OFF!</b> ✨"
            subtitle = f"💎 <b>Fresh Drop Deal!</b> Newly listed on the store with an instant <b>{discount_pct}% discount</b>!"
            button_text = f"🛍️ Grab Deal ({discount_pct}% OFF) ➔"
        else:
            header = "✨ <b>JUST DROPPED ON CASIO INDIA!</b> ✨"
            subtitle = "💎 <b>Fresh Drop Alert!</b> This model was just officially listed on the store!"
            button_text = "🛍️ Grab New Arrival ➔"

        caption = (
            f"{header}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"⌚ <b>{title}</b>\n\n"
            f"{subtitle}\n\n"
            f"{price_block}\n"
            "📦 <b>Availability:</b> In Stock & Ready to Ship ✅\n\n"
            "⚡ <i>Be among the very first to get your hands on this piece!</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f'🔗 <a href="{url}">👉 <b>SNAG IT FIRST ON CASIO STORE</b></a>'
        )

    elif alert_type in ("RESTOCK_NORMAL", "RESTOCK_DISCOUNT"):
        if has_discount:
            header = "🚨💥 <b>RESTOCKED & ON SALE!</b> 💥🚨"
            subtitle = "🔥 <b>Double Win:</b> Back in stock with a heavy discount!"
            button_text = f"🔥 Claim Deal (Save ₹{savings:,.0f}) ➔"
        else:
            header = "🚨 <b>BACK IN STOCK ALERT!</b> 🚨"
            subtitle = "👀 <b>Missed it earlier? It’s finally back!</b>"
            button_text = "⚡ Buy Before It Sells Out ➔"

        caption = (
            f"{header}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"⌚ <b>{title}</b>\n\n"
            f"{subtitle}\n\n"
            f"{price_block}\n"
            "📦 <b>Stock Status:</b> <b>RESTOCKED & READY TO SHIP!</b> 🟢\n\n"
            "⏳ <i>Restocked watches on Casio Bhawar often sell out within hours. Act fast!</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f'🔗 <a href="{url}">👉 <b>CLAIM YOURS BEFORE IT IS GONE</b></a>'
        )

    elif alert_type == "PRICE_DROP":
        caption = (
            "⚡⚡ <b>PRICE DROP: EVEN CHEAPER!</b> ⚡⚡\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"⌚ <b>{title}</b>\n\n"
            "📉 <b>Casio just lowered the price AGAIN!</b>\n\n"
            f"{price_block}\n"
            "📦 <b>Stock:</b> In Stock ✅\n\n"
            "🎯 <i>Absolute lowest recorded price on this model!</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f'🔗 <a href="{url}">👉 <b>LOCK IN THE LOWEST PRICE NOW</b></a>'
        )
        button_text = f"💥 Snatch Lowest Price ({discount_pct}% OFF) ➔" if has_discount else "💥 View Price Drop ➔"

    else:  # Default / NEW_DISCOUNT
        caption = (
            "🚨🔥 <b>DISCOUNT JUST DROPPED!</b> 🔥🚨\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"⌚ <b>{title}</b>\n\n"
            f"💥 <b>Price slashed by {discount_pct}% right now!</b>\n\n"
            f"{price_block}\n"
            "📦 <b>Stock:</b> In Stock & Shippable ✅\n\n"
            "⚡ <i>Random Casio discounts don't last long. Snag it while active!</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f'🔗 <a href="{url}">👉 <b>GRAB THIS DEAL BEFORE IT EXPIRES</b></a>'
        )
        button_text = f"🛒 Buy Now (Save ₹{savings:,.0f}) ➔"

    reply_markup = {
        "inline_keyboard": [
            [{"text": button_text, "url": url}]
        ]
    }

    return caption, reply_markup


def send_telegram_alert(
    bot_token: str,
    chat_id: str,
    alert_type: str,
    title: str,
    price: float,
    compare_at: float,
    discount_pct: float,
    savings: float,
    url: str,
    image_url: Optional[str] = None
) -> bool:
    """Send formatted rich notification to one or multiple Telegram chat/channel IDs."""
    if not bot_token or not chat_id:
        logger.error("Telegram Bot Token or Chat ID not configured!")
        return False

    targets = [c.strip() for c in str(chat_id).split(",") if c.strip()]
    if not targets:
        return False

    caption, reply_markup = format_catchy_alert(
        alert_type=alert_type,
        title=title,
        price=price,
        compare_at=compare_at,
        discount_pct=discount_pct,
        savings=savings,
        url=url
    )

    all_success = True
    for target_id in targets:
        sent = False
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
                        logger.info(f"Telegram photo alert sent to {target_id} [{alert_type}]: {title}")
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
                        logger.info(f"Telegram text alert sent to {target_id} [{alert_type}]: {title}")
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
    notify_new_listings: bool = True,
    notify_restocks: bool = True,
    notify_discounts: bool = True,
    notify_all_new: bool = False,
    dry_run: bool = False
) -> int:
    """Scan product catalog and trigger catchy alerts for new listings, restocks, and price drops."""
    state = load_state(state_file)
    products = get_all_products(scan_all=scan_all)
    alerts_triggered = 0
    state_changed = False

    is_baseline_seed = len(state) == 0 and not notify_all_new
    if is_baseline_seed:
        logger.info(
            f"State database is empty. Performing silent baseline initialization for {len(products)} products "
            "(preventing initial spam). Future scans will trigger alerts on new arrivals, restocks & discounts."
        )

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
                compare_at = float(variant.get("compare_at_price") or price)
            except (ValueError, TypeError):
                continue

            has_discount = compare_at > price and price > 0
            discount_pct = round(((compare_at - price) / compare_at) * 100, 1) if has_discount else 0.0
            savings = round(compare_at - price, 2) if has_discount else 0.0

            prev_record = state.get(key)
            trigger_alert = False
            alert_type = None

            # -------------------------------------------------------------
            # CASE 1: Brand New Listing (never seen in state)
            # -------------------------------------------------------------
            if prev_record is None:
                state_changed = True
                state[key] = {
                    "title": product_title,
                    "price": price,
                    "compare_at": compare_at,
                    "discount_pct": discount_pct,
                    "available": is_available
                }

                if not is_baseline_seed and is_available and notify_new_listings:
                    trigger_alert = True
                    alert_type = "NEW_LISTING"

            # -------------------------------------------------------------
            # CASE 2: Existing Product Check
            # -------------------------------------------------------------
            else:
                prev_price = prev_record.get("price", price)
                prev_compare_at = prev_record.get("compare_at", compare_at)
                prev_available = prev_record.get("available", False)
                prev_discount = prev_record.get("discount_pct", 0.0)

                # Has anything materially changed?
                has_changed = (
                    prev_price != price or
                    prev_compare_at != compare_at or
                    prev_available != is_available or
                    prev_discount != discount_pct
                )

                if has_changed:
                    state_changed = True

                    # Event A: Back in Stock!
                    if is_available and not prev_available:
                        if has_discount and notify_discounts:
                            trigger_alert = True
                            alert_type = "RESTOCK_DISCOUNT"
                        elif notify_restocks:
                            trigger_alert = True
                            alert_type = "RESTOCK_NORMAL"

                    # Event B: New Discount applied to previously full-price item
                    elif is_available and has_discount and prev_discount == 0.0 and discount_pct >= min_discount:
                        if notify_discounts:
                            trigger_alert = True
                            alert_type = "NEW_DISCOUNT"

                    # Event C: Further Price Drop on an already discounted item
                    elif is_available and has_discount and price < prev_price and discount_pct >= min_discount:
                        if notify_discounts:
                            trigger_alert = True
                            alert_type = "PRICE_DROP"

                    state[key] = {
                        "title": product_title,
                        "price": price,
                        "compare_at": compare_at,
                        "discount_pct": discount_pct,
                        "available": is_available
                    }

            if trigger_alert and alert_type:
                alerts_triggered += 1
                logger.info(
                    f"[{alert_type}] {product_title} | ₹{price:,.2f} "
                    f"({f'{discount_pct}% OFF' if discount_pct > 0 else 'Full Price'})"
                )
                if dry_run:
                    logger.info("  -> [DRY-RUN] Telegram alert skipped.")
                else:
                    send_telegram_alert(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        alert_type=alert_type,
                        title=product_title,
                        price=price,
                        compare_at=compare_at,
                        discount_pct=discount_pct,
                        savings=savings,
                        url=product_url,
                        image_url=image_url
                    )
                    time.sleep(1.0)

    if not dry_run and state_changed:
        save_state(state_file, state)
        logger.info(f"State saved ({len(state)} variants tracked). Alerts sent: {alerts_triggered}")
    elif not dry_run:
        logger.info("No price, stock, or catalog changes detected. State file unchanged.")
    else:
        logger.info(f"Dry run complete. Potential alerts detected: {alerts_triggered}")

    return alerts_triggered


def test_scenario_templates(bot_token: str, chat_id: str) -> None:
    """Send preview cards for all 5 catchy scenarios directly to Telegram."""
    logger.info("Sending preview cards for all 5 catchy scenarios to Telegram...")
    test_cases = [
        (
            "NEW_LISTING",
            "Casio G-Shock GA-B2100CD-1A Carbon Core Guard",
            11995.0,
            11995.0,
            0.0,
            0.0,
            "https://casiostore.bhawar.com/collections/watches",
            "https://cdn.shopify.com/s/files/1/0910/0073/3977/files/GA-2100RL-1A.png"
        ),
        (
            "RESTOCK_NORMAL",
            "Casio Vintage A168WEM-1D Silver Digital Classic",
            2695.0,
            2695.0,
            0.0,
            0.0,
            "https://casiostore.bhawar.com/collections/watches",
            "https://cdn.shopify.com/s/files/1/0910/0073/3977/files/GA-2100RL-1A.png"
        ),
        (
            "RESTOCK_DISCOUNT",
            "G-Shock GM-2110D-3A Metal Octagon Bezel Green Dial",
            15396.50,
            21995.0,
            30.0,
            6598.50,
            "https://casiostore.bhawar.com/collections/watches",
            "https://cdn.shopify.com/s/files/1/0910/0073/3977/files/GA-2100RL-1A.png"
        ),
        (
            "NEW_DISCOUNT",
            "Casio G-Shock GMA-P2110SC-4A Compact Octagon",
            6646.50,
            9495.0,
            30.0,
            2848.50,
            "https://casiostore.bhawar.com/collections/watches",
            "https://cdn.shopify.com/s/files/1/0910/0073/3977/files/GA-2100RL-1A.png"
        ),
        (
            "PRICE_DROP",
            "Casio Enticer LTP-SN5YL-3A Gold Tone Women's Watch",
            1647.50,
            3295.0,
            50.0,
            1647.50,
            "https://casiostore.bhawar.com/collections/watches",
            "https://cdn.shopify.com/s/files/1/0910/0073/3977/files/GA-2100RL-1A.png"
        )
    ]

    for alert_type, title, price, compare_at, discount_pct, savings, url, image_url in test_cases:
        logger.info(f"Sending sample card for: {alert_type}...")
        send_telegram_alert(
            bot_token=bot_token,
            chat_id=chat_id,
            alert_type=alert_type,
            title=title,
            price=price,
            compare_at=compare_at,
            discount_pct=discount_pct,
            savings=savings,
            url=url,
            image_url=image_url
        )
        time.sleep(1.2)

    logger.info("All 5 preview template cards successfully delivered to Telegram!")


def main():
    parser = argparse.ArgumentParser(description="Real-Time Casio India Discount, Restock & New Listing Alert Bot")
    parser.add_argument("--once", action="store_true", help="Run a single scan and exit (for GitHub Actions / Cron)")
    parser.add_argument("--interval", type=int, default=None, help="Polling interval in seconds (default: from .env or 120)")
    parser.add_argument("--min-discount", type=float, default=None, help="Minimum discount percentage to trigger alert (e.g. 10 for 10 percent)")
    parser.add_argument("--dry-run", action="store_true", help="Scan without sending Telegram notifications or updating state")
    parser.add_argument("--test-templates", action="store_true", help="Send preview cards of all 5 catchy scenarios to Telegram and exit")
    parser.add_argument("--test-telegram", action="store_true", help="Send a single test message to Telegram and exit")
    parser.add_argument("--all-products", action="store_true", help="Scan all store products instead of just /collections/watches")
    parser.add_argument("--state-file", type=str, default=DEFAULT_STATE_FILE, help="Path to state.json")
    parser.add_argument("--reset-state", action="store_true", help="Clear stored state file before running")
    parser.add_argument("--notify-all-new", action="store_true", help="If state is empty, alert for every single item instead of baseline seeding")

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

    notify_new_listings = os.getenv("NOTIFY_NEW_LISTINGS", "true").lower() == "true"
    notify_restocks = os.getenv("NOTIFY_RESTOCKS", "true").lower() == "true"
    notify_discounts = os.getenv("NOTIFY_DISCOUNTS", "true").lower() == "true"

    interval = args.interval
    if interval is None:
        try:
            interval = int(os.getenv("CHECK_INTERVAL_SECONDS", "120"))
        except ValueError:
            interval = 120

    if args.reset_state and os.path.exists(args.state_file):
        os.remove(args.state_file)
        logger.info(f"Reset state file: {args.state_file}")

    if args.test_templates or args.test_telegram:
        if not bot_token or not chat_id:
            logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment or .env file.")
            sys.exit(1)
        if args.test_templates:
            test_scenario_templates(bot_token, chat_id)
        else:
            test_scenario_templates(bot_token, chat_id)
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
    logger.info("Casio India Tracker: Deals, Restocks & New Arrivals")
    logger.info(f"Scope: {scope_name}")
    logger.info(f"Min Discount Threshold: {min_discount}%")
    logger.info(f"Notify New Listings: {notify_new_listings}")
    logger.info(f"Notify Restocks: {notify_restocks}")
    logger.info(f"Notify Discounts: {notify_discounts}")
    logger.info(f"Mode: {mode_name}")
    logger.info(f"Dry Run: {args.dry_run}")
    logger.info("=" * 60)

    if args.once:
        run_scan(
            bot_token=bot_token,
            chat_id=chat_id,
            state_file=args.state_file,
            min_discount=min_discount,
            scan_all=scan_all,
            notify_new_listings=notify_new_listings,
            notify_restocks=notify_restocks,
            notify_discounts=notify_discounts,
            notify_all_new=args.notify_all_new,
            dry_run=args.dry_run
        )
    else:
        while True:
            try:
                run_scan(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    state_file=args.state_file,
                    min_discount=min_discount,
                    scan_all=scan_all,
                    notify_new_listings=notify_new_listings,
                    notify_restocks=notify_restocks,
                    notify_discounts=notify_discounts,
                    notify_all_new=args.notify_all_new,
                    dry_run=args.dry_run
                )
            except Exception as e:
                logger.error(f"Unexpected error during scan: {e}", exc_info=True)
            logger.info(f"Sleeping for {interval} seconds until next check...")
            time.sleep(interval)


if __name__ == "__main__":
    main()
