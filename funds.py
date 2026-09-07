"""
HAMZZY IG SHOP - COMPLETE STANDALONE BOT
- Email Only and Email + Password options
- Password option: +₦500 to price
- Admin manually adds email + password
- Full working telepython bot
"""

import sqlite3
import time
import random
import os
import re
import datetime
from telegram import *
from telegram.ext import *

# =================================================================================
# CONFIGURATION
# =================================================================================

BOT_TOKEN = "8414986694:AAFaubQgLIpwROLwE8QQl7PaR6WOeVH8uKA"
ADMIN_ID = 7443685686
BOT_USERNAME = "your_ig_bot_username"

BANK_NAME = "OPAY"
ACCOUNT_NUMBER = "9032741650"
ACCOUNT_NAME = "MUHAMMED JAMIU HAMZA"

REFERRAL_BONUS = 250
MIN_DEPOSIT = 500
MIN_WITHDRAWAL = 5000

MY_SIGNATURE = "@hamzzyhacket"
PASSWORD_EXTRA = 500  # Extra Naira for password option

# IG Products - Base prices (email only)
IG_PRODUCTS = {
    "0": 1000,
    "30-40": 1500,
    "50-80": 2000,
    "90-100": 3000,
    "200": 4000,
    "300": 5000,
    "400": 5500,
    "500": 6000,
    "600": 6500,
    "700": 7000,
    "800": 7500,
    "900": 8000,
    "1000": 8500
}

# Product display names with price
def get_product_display(amount, with_password=False):
    price = IG_PRODUCTS[amount]
    if with_password:
        price += PASSWORD_EXTRA
    return f"{amount} followers - ₦{price}"

# =================================================================================
# DATABASE
# =================================================================================

DB_PATH = "ig_bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Restock logs
    c.execute("CREATE TABLE IF NOT EXISTS restock_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, product_name TEXT, quantity INTEGER, restock_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    
    # Users
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, username TEXT, first_name TEXT, referral_code TEXT UNIQUE, referred_by INTEGER, total_referrals INTEGER DEFAULT 0, referral_earnings INTEGER DEFAULT 0, join_date TEXT, last_active TEXT, total_spent INTEGER DEFAULT 0, total_orders INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0)")
    
    # Transactions
    c.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, amount INTEGER, details TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    
    # Stats
    c.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER)")
    
    # Deposits
    c.execute("CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, sender_name TEXT, ref TEXT, amount INTEGER DEFAULT 0, status TEXT DEFAULT 'pending', decline_reason TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    
    # Reports
    c.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, issue_type TEXT, description TEXT, screenshot_id TEXT, status TEXT DEFAULT 'open', admin_response TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    
    # Referrals
    c.execute("CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_id INTEGER UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS referral_earnings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, from_user_id INTEGER)")
    
    # Broadcast logs
    c.execute("CREATE TABLE IF NOT EXISTS broadcast_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, message TEXT, total_sent INTEGER, total_failed INTEGER, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    
    # Sales log
    c.execute("CREATE TABLE IF NOT EXISTS sales_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_name TEXT, amount INTEGER, sale_date DATE)")
    
    # IG Stock - Email Only
    c.execute("CREATE TABLE IF NOT EXISTS ig_stock (id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT, email TEXT, has_password INTEGER DEFAULT 0, password TEXT, status TEXT DEFAULT 'available', added_by INTEGER, added_date TEXT, sold_date TEXT, sold_to INTEGER)")
    
    # IG Stock - Email + Password
    c.execute("CREATE TABLE IF NOT EXISTS ig_stock_password (id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT, email TEXT, password TEXT, status TEXT DEFAULT 'available', added_by INTEGER, added_date TEXT, sold_date TEXT, sold_to INTEGER)")
    
    # IG Cart
    c.execute("CREATE TABLE IF NOT EXISTS ig_cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_name TEXT, price INTEGER, quantity INTEGER DEFAULT 1, has_password INTEGER DEFAULT 0)")
    
    # IG Orders
    c.execute("CREATE TABLE IF NOT EXISTS ig_orders (order_id TEXT PRIMARY KEY, user_id INTEGER, product_name TEXT, amount INTEGER, delivery_info TEXT, order_date TEXT, status TEXT DEFAULT 'completed')")
    
    # Support messages
    c.execute("CREATE TABLE IF NOT EXISTS support_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, screenshot_id TEXT, timestamp TEXT)")
    
    conn.commit()
    
    # Initialize stats
    for k in ["revenue", "orders"]:
        c.execute("INSERT OR IGNORE INTO stats (key, value) VALUES (?, 0)", (k,))
    
    conn.commit()
    conn.close()
    print("✅ IG Database initialized")

init_db()

# =================================================================================
# DATABASE HELPERS
# =================================================================================

conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r[0] if r else 0

def add_user(user_id, username=None, first_name=None):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, balance, join_date, last_active) VALUES (?, ?, ?, 0, ?, ?)",
                   (user_id, username, first_name, datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
    conn.commit()

def update_wallet(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def update_stat(key, value):
    cursor.execute("UPDATE stats SET value = value + ? WHERE key = ?", (value, key))
    conn.commit()

def get_stat(key):
    cursor.execute("SELECT value FROM stats WHERE key = ?", (key,))
    r = cursor.fetchone()
    return r[0] if r else 0

def log_transaction(user_id, t_type, amount, details):
    cursor.execute("INSERT INTO transactions (user_id, type, amount, details) VALUES (?, ?, ?, ?)",
                   (user_id, t_type, amount, details))
    conn.commit()

def generate_ref():
    return f"REF-{random.randint(100000, 999999)}"

def generate_order_id(prefix, user_id):
    return f"{prefix}{user_id}{int(time.time())}{random.randint(100, 999)}"

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_banned(user_id):
    cursor.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r[0] == 1 if r else False

def ban_user(user_id):
    cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def unban_user(user_id):
    cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()

def generate_referral_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

# =================================================================================
# IG STOCK HELPERS
# =================================================================================

def get_ig_stock_count(product_name, require_password=False):
    if require_password:
        cursor.execute("SELECT COUNT(*) FROM ig_stock_password WHERE product_name=? AND status='available'", (product_name,))
    else:
        cursor.execute("SELECT COUNT(*) FROM ig_stock WHERE product_name=? AND status='available'", (product_name,))
    return cursor.fetchone()[0]

def get_all_ig_stock():
    stock = {}
    for name in IG_PRODUCTS:
        cursor.execute("SELECT COUNT(*) FROM ig_stock WHERE product_name=? AND status='available'", (name,))
        email_only = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ig_stock_password WHERE product_name=? AND status='available'", (name,))
        with_password = cursor.fetchone()[0]
        stock[name] = {"email_only": email_only, "with_password": with_password}
    return stock

def get_ig_item(product_name, require_password=False):
    if require_password:
        cursor.execute("SELECT id, email, password FROM ig_stock_password WHERE product_name=? AND status='available' LIMIT 1", (product_name,))
        r = cursor.fetchone()
        return r
    else:
        cursor.execute("SELECT id, email FROM ig_stock WHERE product_name=? AND status='available' LIMIT 1", (product_name,))
        r = cursor.fetchone()
        return r

def get_ig_items(product_name, quantity, require_password=False):
    if require_password:
        cursor.execute("SELECT id, email, password FROM ig_stock_password WHERE product_name=? AND status='available' LIMIT ?", (product_name, quantity))
    else:
        cursor.execute("SELECT id, email FROM ig_stock WHERE product_name=? AND status='available' LIMIT ?", (product_name, quantity))
    return cursor.fetchall()

def mark_ig_sold(item_id, user_id, require_password=False):
    if require_password:
        cursor.execute("UPDATE ig_stock_password SET status='sold', sold_date=?, sold_to=? WHERE id=?", 
                       (datetime.datetime.now().isoformat(), user_id, item_id))
    else:
        cursor.execute("UPDATE ig_stock SET status='sold', sold_date=?, sold_to=? WHERE id=?", 
                       (datetime.datetime.now().isoformat(), user_id, item_id))
    conn.commit()

def add_ig_stock(product_name, email, admin_id, password=None):
    """Add IG stock - can be email only or with password"""
    if password:
        # Add to password table
        cursor.execute("INSERT INTO ig_stock_password (product_name, email, password, added_by, added_date, status) VALUES (?, ?, ?, ?, ?, 'available')",
                       (product_name, email, password, admin_id, datetime.datetime.now().isoformat()))
    else:
        # Add to email only table
        cursor.execute("INSERT INTO ig_stock (product_name, email, added_by, added_date, status) VALUES (?, ?, ?, ?, 'available')",
                       (product_name, email, admin_id, datetime.datetime.now().isoformat()))
    conn.commit()
    return True

def add_bulk_ig_stock(product_name, emails, admin_id, password=None):
    added = 0
    for email in emails:
        if add_ig_stock(product_name, email, admin_id, password):
            added += 1
    return added

def clear_all_ig_stock():
    cursor.execute("DELETE FROM ig_stock")
    cursor.execute("DELETE FROM ig_stock_password")
    conn.commit()

def clear_ig_product(product_name):
    cursor.execute("DELETE FROM ig_stock WHERE product_name=?", (product_name,))
    cursor.execute("DELETE FROM ig_stock_password WHERE product_name=?", (product_name,))
    conn.commit()

def extract_ig_stock(product_name, with_password=False):
    if with_password:
        cursor.execute("SELECT email, password FROM ig_stock_password WHERE product_name=? AND status='available'", (product_name,))
        rows = cursor.fetchall()
        return [(row[0], row[1]) for row in rows]
    else:
        cursor.execute("SELECT email FROM ig_stock WHERE product_name=? AND status='available'", (product_name,))
        rows = cursor.fetchall()
        return [row[0] for row in rows]

def get_product_price(product_name, with_password=False):
    base_price = IG_PRODUCTS.get(product_name, 0)
    if with_password:
        return base_price + PASSWORD_EXTRA
    return base_price

# =================================================================================
# IG CART HELPERS
# =================================================================================

def get_cart(user_id):
    cursor.execute("SELECT id, product_name, price, quantity, has_password FROM ig_cart WHERE user_id=?", (user_id,))
    return cursor.fetchall()

def add_to_cart(user_id, product_name, price, has_password=0):
    cursor.execute("SELECT id, quantity FROM ig_cart WHERE user_id=? AND product_name=? AND has_password=?", (user_id, product_name, has_password))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE ig_cart SET quantity=quantity+1 WHERE id=?", (row[0],))
    else:
        cursor.execute("INSERT INTO ig_cart (user_id, product_name, price, quantity, has_password) VALUES (?, ?, ?, 1, ?)", (user_id, product_name, price, has_password))
    conn.commit()

def remove_from_cart(user_id, cart_id):
    cursor.execute("DELETE FROM ig_cart WHERE id=? AND user_id=?", (cart_id, user_id))
    conn.commit()

def clear_cart(user_id):
    cursor.execute("DELETE FROM ig_cart WHERE user_id=?", (user_id,))
    conn.commit()

def get_cart_total(user_id):
    cursor.execute("SELECT SUM(price * quantity) FROM ig_cart WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r[0] if r[0] else 0

# =================================================================================
# IG ORDER HELPERS
# =================================================================================

def create_ig_order(user_id, product_name, amount, delivery_info):
    order_id = generate_order_id("IGORD", user_id)
    cursor.execute("INSERT INTO ig_orders (order_id, user_id, product_name, amount, delivery_info, order_date) VALUES (?, ?, ?, ?, ?, ?)",
                   (order_id, user_id, product_name, amount, delivery_info, datetime.datetime.now().isoformat()))
    cursor.execute("UPDATE users SET total_spent = total_spent + ?, total_orders = total_orders + 1 WHERE user_id = ?", (amount, user_id))
    conn.commit()
    return order_id

# =================================================================================
# BOT STATE
# =================================================================================

pending_approvals = {}
fraud_tracker = {}
blocked_users = set()
user_support_mode = {}
user_sessions = {}

# =================================================================================
# KEYBOARDS
# =================================================================================

def get_main_menu(user_id):
    cart_count = len(get_cart(user_id))
    cart_text = f" | 🛒 {cart_count} items" if cart_count > 0 else ""
    
    menu = [
        ["💰 Wallet", "➕ Fund Wallet"],
        ["📦 Check Stock", "🧾 My History"],
        ["💳 My Deposits", "🛒 Buy Products"],
        ["🤖 Expert Support", "📝 Report Issue"],
        ["🤝 Refer & Earn", "🛒 My Cart"],
        ["📋 Help & FAQ"]
    ]
    if is_admin(user_id):
        menu.append(["👑 Admin Panel"])
    return ReplyKeyboardMarkup(menu, resize_keyboard=True)

def get_ig_admin_panel():
    kb = [
        ["📊 Stats", "📥 Pending"],
        ["📝 Reports", "💰 Add Funds"],
        ["💸 Deduct Funds", "📈 Sales"],
        ["📦 Restock", "📢 Broadcast"],
        ["💬 Message User", "👤 View Balance"],
        ["🚫 Block/Unblock", "🗑 Clear Stock"],
        ["📤 Extract Stock", "🔄 User Menu"]
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# =================================================================================
# START COMMAND
# =================================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or ""
    first_name = update.message.from_user.first_name or "User"
    
    add_user(user_id, username, first_name)
    user_support_mode.pop(user_id, None)
    
    # Handle referral
    if context.args and context.args[0].startswith("ref_"):
        try:
            referrer_id = int(context.args[0].replace("ref_", ""))
            if referrer_id != user_id:
                cursor.execute("SELECT id FROM referrals WHERE referred_id=?", (user_id,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
                    cursor.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
                    conn.commit()
                    # Process referral bonus
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (REFERRAL_BONUS, referrer_id))
                    cursor.execute("UPDATE users SET total_referrals = total_referrals + 1, referral_earnings = referral_earnings + ? WHERE user_id = ?", (REFERRAL_BONUS, referrer_id))
                    cursor.execute("INSERT INTO referral_earnings (user_id, amount, from_user_id) VALUES (?, ?, ?)", (referrer_id, REFERRAL_BONUS, user_id))
                    log_transaction(referrer_id, "credit", REFERRAL_BONUS, f"referral_from_{user_id}")
                    conn.commit()
                    try:
                        await context.bot.send_message(referrer_id, f"🎉 New referral! +₦{REFERRAL_BONUS}")
                    except:
                        pass
        except:
            pass
    
    cart_count = len(get_cart(user_id))
    cart_text = f" | 🛒 {cart_count} items" if cart_count > 0 else ""
    
    welcome = f"""
📱 **WELCOME TO IG SHOP!**

🔥 Hello {first_name}!
✅ 100% LEGIT & ACTIVE

📌 Buy Instagram accounts with email delivery!
🤝 Earn ₦{REFERRAL_BONUS} per referral!

📌 Select a package below to buy.

💀 @hamzzyhacket
"""
    
    await update.message.reply_text(
        welcome,
        reply_markup=get_main_menu(user_id),
        parse_mode='HTML'
    )

# =================================================================================
# WALLET & FUND
# =================================================================================

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    bal = get_balance(user_id)
    await update.message.reply_text(f"💰 **Your Balance: ₦{bal}**", parse_mode='HTML')

async def fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ref = generate_ref()
    context.user_data["fund_ref"] = ref
    context.user_data["awaiting_name"] = True
    await update.message.reply_text(
        f"💳 **FUND YOUR WALLET**\n\n"
        f"🏦 {BANK_NAME}\n"
        f"🔢 {ACCOUNT_NUMBER}\n"
        f"👤 {ACCOUNT_NAME}\n\n"
        f"🆔 {ref}\n\n"
        f"📝 Send SENDER NAME first.\n\n"
        f"Type /cancel to cancel.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ I've Made Payment", callback_data=f"pay:{ref}")]
        ]),
        parse_mode='HTML'
    )

# =================================================================================
# CHECK STOCK
# =================================================================================

async def user_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📦 **STOCK**\n\n"
    msg += "📧 Email Only | 🔐 Email + Password\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    stock = get_all_ig_stock()
    
    for name, counts in stock.items():
        price = IG_PRODUCTS[name]
        price_with_pass = price + PASSWORD_EXTRA
        email_count = counts['email_only']
        pass_count = counts['with_password']
        total = email_count + pass_count
        
        status = "✅" if total > 0 else "❌"
        
        # Show product with both options in one line
        msg += f"{status} {name} followers\n"
        msg += f"   📧 {email_count} @ ₦{price}  |  🔐 {pass_count} @ ₦{price_with_pass}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    await update.message.reply_text(msg, parse_mode='HTML')

# =================================================================================
# HISTORY / DEPOSITS / SUPPORT / REPORT / FAQ / REFER
# =================================================================================

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("SELECT type, amount, details, timestamp FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,))
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("📭 No transactions yet")
        return
    msg = "🧾 **YOUR HISTORY**\n\n"
    for r in rows:
        emoji = "➕" if r['type'] == 'credit' else "➖"
        msg += f"{emoji} ₦{r['amount']} - {r['details']}\n"
        msg += f"   📅 {r['timestamp'][:16]}\n\n"
    await update.message.reply_text(msg, parse_mode='HTML')

async def my_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("SELECT ref, amount, status, decline_reason FROM deposits WHERE user_id=? ORDER BY id DESC LIMIT 5", (user_id,))
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("📭 No deposits yet")
        return
    msg = "💳 **YOUR DEPOSITS**\n\n"
    for r in rows:
        emoji = "✅" if r['status'] == 'approved' else "⏳" if r['status'] == 'pending' else "❌"
        msg += f"{emoji} {r['ref']}: ₦{r['amount'] if r['amount'] else '...'} ({r['status']})\n"
        if r['decline_reason']:
            msg += f"   📋 {r['decline_reason']}\n"
    await update.message.reply_text(msg, parse_mode='HTML')

async def expert_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_support_mode[user_id] = True
    await update.message.reply_text(
        "🤖 **EXPERT SUPPORT**\n\n"
        "Describe your issue or question in detail.\n"
        "Type 'exit' to leave.\n\n"
        "💎 @hamzzyhacket",
        reply_markup=ReplyKeyboardMarkup([["❌ Exit Support"]], resize_keyboard=True),
        parse_mode='HTML'
    )

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    if text == "❌ Exit Support":
        user_support_mode.pop(user_id, None)
        await start(update, context)
        return
    
    msg = text.lower()
    if "how" in msg or "work" in msg:
        r = "📋 Buy uncreated Gmail → Create it → Instagram 'Forgot Password' → Reset → Own both!"
    elif "cart" in msg:
        r = "🛒 Use '➕ Cart' to add items → View Cart to manage → Checkout all at once!"
    elif "create" in msg or "gmail" in msg:
        r = "🔧 Gmail.com → Create Account → Enter our address → Create password → Done!"
    elif "price" in msg or "cost" in msg:
        r = "💰 ₦1000-₦8500 (Email Only) | +₦500 for Email + Password"
    elif "pay" in msg or "fund" in msg:
        r = f"💳 Click '➕ Fund Wallet' → Transfer to {BANK_NAME} ({ACCOUNT_NUMBER}) → Send name → Upload screenshot."
    else:
        r = "🤖 Ask me anything!"
    await update.message.reply_text(r)

async def report_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📧 Gmail Taken", callback_data="report_taken")],
        [InlineKeyboardButton("📷 IG Not Linked", callback_data="report_notlinked")],
        [InlineKeyboardButton("💳 Payment", callback_data="report_payment")],
        [InlineKeyboardButton("❓ Other", callback_data="report_other")]
    ]
    await update.message.reply_text("📝 **FILE A REPORT**\n\nSelect type:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    issue_type = query.data.replace("report_", "")
    context.user_data["report_type"] = issue_type
    context.user_data["awaiting_report"] = True
    
    prompts = {
        "taken": "📧 Gmail Already Taken",
        "notlinked": "📷 Instagram Not Linked",
        "payment": "💳 Payment Issue",
        "other": "❓ Other Issue"
    }
    kb = [
        [InlineKeyboardButton("📝 SUBMIT REPORT", callback_data="report_submit")],
        [InlineKeyboardButton("❌ Cancel", callback_data="report_cancel")]
    ]
    await query.edit_message_text(
        f"📝 **{prompts.get(issue_type, 'Report')}**\n\nSend description then click Submit.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='HTML'
    )

async def report_submit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    desc = context.user_data.get("report_desc", "").strip()
    issue_type = context.user_data.get("report_type", "other")
    screenshot_id = context.user_data.get("report_screenshot", None)
    
    if not desc:
        await query.answer("Send description first!", show_alert=True)
        return
    
    issue_names = {
        "taken": "📧 Gmail Already Taken",
        "notlinked": "📷 Instagram Not Linked",
        "payment": "💳 Payment Issue",
        "other": "❓ Other Issue"
    }
    
    cursor.execute("INSERT INTO reports (user_id, issue_type, description, screenshot_id) VALUES (?, ?, ?, ?)",
                   (user_id, issue_type, desc[:500], screenshot_id))
    conn.commit()
    report_id = cursor.lastrowid
    
    try:
        kb = [
            [InlineKeyboardButton("✅ Resolve", callback_data=f"resolve_{report_id}")],
            [InlineKeyboardButton("💬 Reply", callback_data=f"reply_{report_id}")],
            [InlineKeyboardButton("💰 Add Funds", callback_data=f"addfund_{user_id}")]
        ]
        if screenshot_id:
            await context.bot.send_photo(
                ADMIN_ID,
                screenshot_id,
                caption=f"📝 **NEW REPORT #{report_id}**\n\n👤 User ID: {user_id}\n🏷 {issue_names.get(issue_type, issue_type)}\n📄 {desc[:500]}",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                ADMIN_ID,
                f"📝 **NEW REPORT #{report_id}**\n\n👤 User ID: {user_id}\n🏷 {issue_names.get(issue_type, issue_type)}\n📄 {desc[:500]}",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode='HTML'
            )
    except:
        pass
    
    context.user_data.pop("report_type", None)
    context.user_data.pop("report_desc", None)
    context.user_data.pop("report_screenshot", None)
    context.user_data.pop("awaiting_report", None)
    
    await query.edit_message_text(f"✅ **Report #{report_id} Submitted!**")

async def report_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("report_type", None)
    context.user_data.pop("report_desc", None)
    context.user_data.pop("report_screenshot", None)
    context.user_data.pop("awaiting_report", None)
    await query.edit_message_text("❌ Report cancelled.")

async def help_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📋 How It Works", callback_data="faq_how")],
        [InlineKeyboardButton("💳 How to Fund", callback_data="faq_fund")],
        [InlineKeyboardButton("🛒 How to Buy", callback_data="faq_buy")],
        [InlineKeyboardButton("🛒 Using Cart", callback_data="faq_cart")],
        [InlineKeyboardButton("🔄 Replacements", callback_data="faq_replace")]
    ]
    await update.message.reply_text("📋 **HELP & FAQ**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    faq = query.data.replace("faq_", "")
    
    faqs = {
        "how": "📋 Buy uncreated Gmail → Create it → Instagram 'Forgot Password' → Enter Gmail → Reset password → Own both!",
        "fund": f"💳 Transfer to {BANK_NAME} ({ACCOUNT_NUMBER}) - {ACCOUNT_NAME} → Send name → Upload screenshot → Wait approval",
        "buy": "🛒 Fund wallet → Buy Products → Click BUY to purchase instantly → Confirm → Get email!",
        "cart": "🛒 Click ➕ Cart to add items → View Cart to manage → Adjust quantities → Checkout all at once!",
        "replace": "🔄 Replacement if Gmail taken or IG not linked. Report within 1 hour."
    }
    kb = [[InlineKeyboardButton("🔙 Back", callback_data="faq_back")]]
    await query.edit_message_text(faqs.get(faq, "❓ FAQ"), reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def faq_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await help_faq(update, context)

async def refer_earn_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    link = generate_referral_link(user_id)
    
    cursor.execute("SELECT total_referrals, referral_earnings FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    referrals = r[0] if r else 0
    earnings = r[1] if r else 0
    
    await update.message.reply_text(
        f"🤝 **REFER & EARN ₦{REFERRAL_BONUS}**\n\n"
        f"📊 Your Referrals: {referrals}\n"
        f"💰 Earnings: ₦{earnings}\n\n"
        f"🔗 Your Link:\n`{link}`\n\n"
        f"Share this link with friends!\nWhen they join and buy, you get ₦{REFERRAL_BONUS}!",
        parse_mode='Markdown'
    )

# =================================================================================
# BUY PRODUCTS
# =================================================================================

async def buy_products_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📧 Small (0-100)", callback_data="cat_small")],
        [InlineKeyboardButton("📧 Medium (200-500)", callback_data="cat_medium")],
        [InlineKeyboardButton("📧 Large (600-1000)", callback_data="cat_large")],
        [InlineKeyboardButton("📦 All", callback_data="cat_all")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]
    await update.message.reply_text(
        "🛒 **BUY IG PRODUCTS**\n\n"
        "Select category:\n"
        "📧 Email Only | 🔐 Email + Password (+₦500)",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='HTML'
    )

async def product_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.replace("cat_", "")
    
    if data == "small":
        products = {k: v for k, v in IG_PRODUCTS.items() if v <= 3000}
        title = "SMALL (0-100)"
    elif data == "medium":
        products = {k: v for k, v in IG_PRODUCTS.items() if 4000 <= v <= 6000}
        title = "MEDIUM (200-500)"
    elif data == "large":
        products = {k: v for k, v in IG_PRODUCTS.items() if v >= 6500}
        title = "LARGE (600-1000)"
    else:
        products = IG_PRODUCTS
        title = "ALL"
    
    msg = f"**{title}**\n\n"
    msg += "📧 Email Only | 🔐 Email + Password (+₦500)\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "🛒 Click to BUY NOW | 🛒➕ Click to ADD TO CART\n\n"
    kb = []
    for name, price in products.items():
        email_only_count = get_ig_stock_count(name, require_password=False)
        with_pass_count = get_ig_stock_count(name, require_password=True)
        price_with_pass = price + PASSWORD_EXTRA
        
        # Email only row
        msg += f"📧 {name} followers - ₦{price} [{email_only_count} in stock]\n"
        if email_only_count > 0:
            kb.append([
                InlineKeyboardButton(f"📧 BUY {name}", callback_data=f"buy_{name}_0"),
                InlineKeyboardButton(f"➕ Cart", callback_data=f"addcart_{name}_0")
            ])
        
        # Email + Password row
        msg += f"🔐 {name} followers + PW - ₦{price_with_pass} [{with_pass_count} in stock]\n"
        if with_pass_count > 0:
            kb.append([
                InlineKeyboardButton(f"🔐 BUY {name}", callback_data=f"buy_{name}_1"),
                InlineKeyboardButton(f"➕ Cart", callback_data=f"addcart_{name}_1")
            ])
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    kb.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def buy_product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    data = query.data.replace("buy_", "")
    parts = data.rsplit("_", 1)
    if len(parts) != 2:
        return
    product_name, has_password = parts[0], int(parts[1])
    
    if product_name not in IG_PRODUCTS:
        return
    
    price = get_product_price(product_name, has_password)
    if get_ig_stock_count(product_name, require_password=has_password) == 0:
        await query.answer("❌ Out of stock!", show_alert=True)
        return
    
    bal = get_balance(user_id)
    if bal < price:
        await query.answer(f"❌ Insufficient funds! Need ₦{price}, you have ₦{bal}", show_alert=True)
        return
    
    type_text = "🔐 Email + Password" if has_password else "📧 Email Only"
    kb = [
        [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_{product_name}_{has_password}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="back_to_categories")]
    ]
    await query.edit_message_text(
        f"🛒 **CONFIRM PURCHASE**\n\n"
        f"📦 {product_name} followers\n"
        f"📦 Type: {type_text}\n"
        f"💰 Price: ₦{price}\n"
        f"💳 Balance: ₦{bal}\n"
        f"💳 After: ₦{bal-price}\n\n"
        f"Click Confirm to proceed.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='HTML'
    )

async def confirm_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    data = query.data.replace("confirm_", "")
    parts = data.rsplit("_", 1)
    if len(parts) != 2:
        return
    product_name, has_password = parts[0], int(parts[1])
    
    if product_name not in IG_PRODUCTS:
        return
    
    price = get_product_price(product_name, has_password)
    if get_balance(user_id) < price:
        await query.answer("❌ Insufficient funds!", show_alert=True)
        return
    
    item = get_ig_item(product_name, require_password=has_password)
    if not item:
        await query.answer("❌ Out of stock!", show_alert=True)
        return
    
    item_id, email = item[0], item[1]
    password = item[2] if has_password else None
    
    mark_ig_sold(item_id, user_id, require_password=has_password)
    update_wallet(user_id, -price)
    update_stat("revenue", price)
    update_stat("orders", 1)
    log_transaction(user_id, "purchase", price, f"{product_name} followers ({'with PW' if has_password else 'email only'})")
    
    # Log sales
    cursor.execute("INSERT INTO sales_log (user_id, product_name, amount, sale_date) VALUES (?, ?, ?, date('now'))",
                   (user_id, f"{product_name} followers", price))
    conn.commit()
    
    type_text = "🔐 Email + Password" if has_password else "📧 Email Only"
    delivery_info = f"📧 Email: {email}"
    if has_password and password:
        delivery_info += f"\n🔑 Password: {password}"
    
    order_id = create_ig_order(user_id, f"{product_name} followers ({type_text})", price, delivery_info)
    
    await query.edit_message_text(
        f"✅ **PURCHASE COMPLETE!**\n\n"
        f"📦 {product_name} followers\n"
        f"📦 Type: {type_text}\n"
        f"💰 ₦{price}\n"
        f"📧 `{email}`\n"
        + (f"🔑 `{password}`\n" if has_password and password else "") +
        f"\n💳 Balance: ₦{get_balance(user_id)}\n"
        f"📦 Order ID: {order_id[:12]}...\n\n"
        f"💎 {MY_SIGNATURE}",
        parse_mode='Markdown'
    )

async def add_to_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    data = query.data.replace("addcart_", "")
    parts = data.rsplit("_", 1)
    if len(parts) != 2:
        return
    product_name, has_password = parts[0], int(parts[1])
    
    if product_name not in IG_PRODUCTS:
        return
    
    price = get_product_price(product_name, has_password)
    if get_ig_stock_count(product_name, require_password=has_password) == 0:
        await query.answer("❌ Out of stock!", show_alert=True)
        return
    
    add_to_cart(user_id, product_name, price, has_password)
    cart_count = len(get_cart(user_id))
    cart_total = get_cart_total(user_id)
    await query.answer(f"✅ Added! 🛒 {cart_count} items | ₦{cart_total}", show_alert=True)

async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton("📧 Small", callback_data="cat_small")],
        [InlineKeyboardButton("📧 Medium", callback_data="cat_medium")],
        [InlineKeyboardButton("📧 Large", callback_data="cat_large")],
        [InlineKeyboardButton("📦 All", callback_data="cat_all")]
    ]
    await query.edit_message_text(
        "🛒 **BUY IG PRODUCTS**\n\n"
        "Select category:\n"
        "📧 Email Only | 🔐 Email + Password (+₦500)",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode='HTML'
    )

# =================================================================================
# CART
# =================================================================================

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    items = get_cart(user_id)
    
    if not items:
        kb = [[InlineKeyboardButton("🛒 Browse Products", callback_data="cat_all")]]
        await update.message.reply_text("🛒 Cart empty!", reply_markup=InlineKeyboardMarkup(kb))
        return
    
    total = get_cart_total(user_id)
    bal = get_balance(user_id)
    msg = f"🛒 **YOUR CART**\n\n"
    kb = []
    
    for item in items:
        cart_id, pn, pr, qty, hp = item
        type_text = "🔐" if hp else "📧"
        msg += f"{type_text} {pn} followers\n   Qty: {qty} × ₦{pr} = ₦{pr*qty}\n\n"
        kb.append([
            InlineKeyboardButton(f"➕ Add more", callback_data=f"qtyadd_{cart_id}"),
            InlineKeyboardButton(f"➖ Remove one", callback_data=f"qtysub_{cart_id}"),
            InlineKeyboardButton(f"❌ Remove all", callback_data=f"rmcart_{cart_id}")
        ])
    
    msg += f"━━━━━━━━━━━━━━━\n💰 **Total: ₦{total}**\n💳 Balance: ₦{bal}\n"
    if total > 0:
        if bal >= total:
            msg += f"\n✅ You have enough funds!"
            kb.append([InlineKeyboardButton("✅ CHECKOUT NOW", callback_data="checkout")])
        else:
            msg += f"\n⚠️ Insufficient! Need ₦{total - bal} more."
    
    kb.append([InlineKeyboardButton("🗑 Clear Cart", callback_data="clearcart")])
    kb.append([InlineKeyboardButton("🛒 Continue Shopping", callback_data="cat_all")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("rmcart_"):
        cart_id = int(data.replace("rmcart_", ""))
        remove_from_cart(user_id, cart_id)
        await view_cart(update, context)
        return
    
    if data.startswith("qtyadd_"):
        cart_id = int(data.replace("qtyadd_", ""))
        cursor.execute("UPDATE ig_cart SET quantity=quantity+1 WHERE id=? AND user_id=?", (cart_id, user_id))
        conn.commit()
        await view_cart(update, context)
        return
    
    if data.startswith("qtysub_"):
        cart_id = int(data.replace("qtysub_", ""))
        cursor.execute("SELECT quantity FROM ig_cart WHERE id=? AND user_id=?", (cart_id, user_id))
        row = cursor.fetchone()
        if row and row[0] > 1:
            cursor.execute("UPDATE ig_cart SET quantity=quantity-1 WHERE id=?", (cart_id,))
            conn.commit()
        else:
            remove_from_cart(user_id, cart_id)
        await view_cart(update, context)
        return
    
    if data == "clearcart":
        clear_cart(user_id)
        await query.edit_message_text("🛒 Cart cleared!")
        return
    
    if data == "checkout":
        await checkout_cart(update, context)
        return

async def checkout_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    items = get_cart(user_id)
    if not items:
        await query.answer("Cart empty!", show_alert=True)
        return
    
    total = get_cart_total(user_id)
    if get_balance(user_id) < total:
        await query.answer(f"❌ Need ₦{total}!", show_alert=True)
        return
    
    # Check stock for all items
    for item in items:
        _, pn, _, _, hp = item
        if get_ig_stock_count(pn, require_password=hp) < item[3]:
            await query.edit_message_text(f"❌ Not enough stock for {pn}!")
            return
    
    delivered = []
    total_spent = 0
    
    for item in items:
        cart_id, pn, pr, qty, hp = item
        for stock_item in get_ig_items(pn, qty, require_password=hp):
            mark_ig_sold(stock_item[0], user_id, require_password=hp)
            email = stock_item[1]
            password = stock_item[2] if hp else None
            type_text = "🔐" if hp else "📧"
            delivered.append(f"{type_text} {pn}: {email}" + (f" (PW: {password})" if password else ""))
            total_spent += pr
            update_stat("revenue", pr)
            update_stat("orders", 1)
            log_transaction(user_id, "purchase", pr, f"{pn} followers ({'with PW' if hp else 'email only'})")
            cursor.execute("INSERT INTO sales_log (user_id, product_name, amount, sale_date) VALUES (?, ?, ?, date('now'))",
                          (user_id, f"{pn} followers", pr))
            conn.commit()
    
    update_wallet(user_id, -total_spent)
    clear_cart(user_id)
    
    await query.edit_message_text(
        f"✅ **ORDER COMPLETE!**\n\n"
        + "\n".join(delivered) +
        f"\n\n💰 Total: ₦{total_spent}\n"
        f"💳 Remaining: ₦{get_balance(user_id)}",
        parse_mode='HTML'
    )

# =================================================================================
# ADMIN PANEL
# =================================================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only!")
        return
    await update.message.reply_text("👑 **IG ADMIN PANEL**", reply_markup=get_ig_admin_panel(), parse_mode='HTML')

async def switch_to_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# =================================================================================
# ADMIN: STATS
# =================================================================================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    
    await update.message.reply_text(
        f"📊 **IG STATS**\n\n"
        f"👥 Users: {users}\n"
        f"📦 Orders: {get_stat('orders')}\n"
        f"💰 Revenue: ₦{get_stat('revenue')}",
        parse_mode='HTML'
    )

# =================================================================================
# ADMIN: PENDING DEPOSITS
# =================================================================================

async def admin_pending_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    if not pending_approvals:
        await update.message.reply_text("✅ No pending deposits")
        return
    
    for uid, data in pending_approvals.items():
        kb = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve:{uid}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"reject:{uid}")]
        ]
        try:
            await context.bot.send_photo(
                ADMIN_ID,
                data["photo_id"],
                caption=f"💳 **PENDING DEPOSIT**\n\n"
                        f"👤 User: {uid}\n"
                        f"🏦 {data['sender_name']}\n"
                        f"🔢 {data['ref']}",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode='HTML'
            )
        except:
            pass

# =================================================================================
# ADMIN: REPORTS
# =================================================================================

async def admin_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    cursor.execute("SELECT id, user_id, issue_type, description FROM reports WHERE status='open' ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("✅ No open reports")
        return
    
    for r in rows:
        kb = [
            [InlineKeyboardButton("✅ Resolve", callback_data=f"resolve_{r['id']}")],
            [InlineKeyboardButton("💬 Reply", callback_data=f"reply_{r['id']}")],
            [InlineKeyboardButton("💰 Add Funds", callback_data=f"addfund_{r['user_id']}")]
        ]
        await update.message.reply_text(
            f"📝 #{r['id']} | 👤 {r['user_id']}\n"
            f"🏷 {r['issue_type']}\n"
            f"📄 {r['description'][:200]}",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode='HTML'
        )

# =================================================================================
# ADMIN: ADD FUNDS
# =================================================================================

async def admin_add_funds_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    context.user_data["awaiting_addfund_user"] = True
    await update.message.reply_text(
        "💰 **ADD FUNDS**\n\nEnter USER ID:\nType /cancel to abort.",
        parse_mode='HTML'
    )

async def admin_deduct_funds_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    context.user_data["awaiting_deduct_user"] = True
    await update.message.reply_text(
        "💸 **DEDUCT FUNDS**\n\nEnter USER ID:\nType /cancel to abort.",
        parse_mode='HTML'
    )

# =================================================================================
# ADMIN: SALES
# =================================================================================

async def admin_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM sales_log WHERE sale_date=date('now')")
    td = cursor.fetchone()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM sales_log WHERE sale_date>=date('now','-7 days')")
    wk = cursor.fetchone()
    
    await update.message.reply_text(
        f"📈 **SALES**\n\n"
        f"📆 Today: {td[0] if td else 0} orders, ₦{td[1] if td else 0}\n"
        f"📅 Week: {wk[0] if wk else 0} orders, ₦{wk[1] if wk else 0}\n"
        f"💰 All: ₦{get_stat('revenue')}",
        parse_mode='HTML'
    )

# =================================================================================
# ADMIN: RESTOCK
# =================================================================================

async def admin_restock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    kb = []
    stock = get_all_ig_stock()
    for name, counts in stock.items():
        price = IG_PRODUCTS[name]
        price_with_pass = price + PASSWORD_EXTRA
        kb.append([InlineKeyboardButton(
            f"📧 {name} - ₦{price} ({counts['email_only']}) | 🔐 +PW - ₦{price_with_pass} ({counts['with_password']})",
            callback_data=f"restock_{name}"
        )])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])
    await update.message.reply_text("📦 **RESTOCK**\n\nSelect product to restock:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def restock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        return
    
    if query.data == "back_to_admin":
        await admin_panel(update, context)
        return
    
    product_name = query.data.replace("restock_", "")
    if product_name in IG_PRODUCTS:
        context.user_data["awaiting_restock_file"] = True
        context.user_data["restock_product"] = product_name
        await query.edit_message_text(
            f"📦 **RESTOCK: {product_name} followers**\n\n"
            f"Send a .txt file with emails (one per line).\n\n"
            f"📧 For Email Only: just emails\n"
            f"🔐 For Email + Password: format `email|password`\n"
            f"Example:\n"
            f"user1@gmail.com\n"
            f"user2@gmail.com|pass123\n\n"
            f"Type /cancel to abort.",
            parse_mode='HTML'
        )

# =================================================================================
# ADMIN: BROADCAST
# =================================================================================

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    context.user_data["awaiting_broadcast"] = True
    await update.message.reply_text(
        "📢 **BROADCAST**\n\n"
        "Send your message or photo with caption.\n"
        "Type /cancel to abort.",
        parse_mode='HTML'
    )

# =================================================================================
# ADMIN: MESSAGE USER
# =================================================================================

async def admin_message_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    context.user_data["awaiting_msg_user"] = True
    await update.message.reply_text(
        "💬 **MESSAGE USER**\n\nEnter USER ID:\nType /cancel to abort.",
        parse_mode='HTML'
    )

# =================================================================================
# ADMIN: VIEW BALANCE
# =================================================================================

async def admin_view_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    context.user_data["awaiting_view_balance"] = True
    await update.message.reply_text(
        "👤 **VIEW BALANCE**\n\nEnter USER ID:\nType /cancel to abort.",
        parse_mode='HTML'
    )

# =================================================================================
# ADMIN: BLOCK/UNBLOCK
# =================================================================================

async def admin_block_unblock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    kb = [
        [InlineKeyboardButton("🚫 Block User", callback_data="block_menu")],
        [InlineKeyboardButton("✅ Unblock User", callback_data="unblock_menu")],
        [InlineKeyboardButton("📋 View Blocked", callback_data="blocked_list")]
    ]
    await update.message.reply_text("🚫 **BLOCK/UNBLOCK**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

# =================================================================================
# ADMIN: CLEAR STOCK
# =================================================================================

async def admin_clear_stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    stock = get_all_ig_stock()
    kb = [[InlineKeyboardButton("🗑 CLEAR ALL", callback_data="clearstock_all")]]
    for name, counts in stock.items():
        total = counts['email_only'] + counts['with_password']
        if total > 0:
            kb.append([InlineKeyboardButton(f"🗑 {name} ({total})", callback_data=f"clearstock_{name}")])
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="clearstock_cancel")])
    await update.message.reply_text("🗑 **CLEAR STOCK**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

# =================================================================================
# ADMIN: EXTRACT STOCK
# =================================================================================

async def admin_extract_stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    stock = get_all_ig_stock()
    kb = []
    for name, counts in stock.items():
        total = counts['email_only'] + counts['with_password']
        if total > 0:
            kb.append([InlineKeyboardButton(f"📤 {name} ({total})", callback_data=f"extract_{name}")])
    kb.append([InlineKeyboardButton("📤 ALL", callback_data="extract_all")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])
    await update.message.reply_text("📤 **EXTRACT STOCK**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

# =================================================================================
# ADMIN: CLEAR STOCK CALLBACKS
# =================================================================================

async def clear_stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        return
    
    data = query.data
    
    if data == "clearstock_all":
        clear_all_ig_stock()
        await query.edit_message_text("✅ All stock deleted!")
        return
    
    if data == "clearstock_cancel":
        await query.edit_message_text("❌ Cancelled.")
        return
    
    if data.startswith("clearstock_"):
        product_name = data.replace("clearstock_", "")
        if product_name in IG_PRODUCTS:
            clear_ig_product(product_name)
            await query.edit_message_text(f"✅ {product_name} cleared!")
        return

# =================================================================================
# ADMIN: EXTRACT STOCK CALLBACKS
# =================================================================================

async def extract_stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        return
    
    data = query.data
    
    if data == "extract_all":
        all_emails = []
        for name in IG_PRODUCTS:
            emails = extract_ig_stock(name, with_password=False)
            all_emails.extend(emails)
            pw_emails = extract_ig_stock(name, with_password=True)
            all_emails.extend([f"{e[0]}|{e[1]}" for e in pw_emails])
        if not all_emails:
            await query.edit_message_text("❌ No stock!")
            return
        content = "\n".join(all_emails)
        await query.edit_message_text(f"📤 **All Stock**\n\n{content[:2000]}")
        return
    
    if data.startswith("extract_"):
        product_name = data.replace("extract_", "")
        if product_name in IG_PRODUCTS:
            emails = extract_ig_stock(product_name, with_password=False)
            pw_emails = extract_ig_stock(product_name, with_password=True)
            if not emails and not pw_emails:
                await query.edit_message_text(f"❌ No stock for {product_name}")
                return
            content = ""
            if emails:
                content += "📧 Email Only:\n" + "\n".join(emails) + "\n\n"
            if pw_emails:
                content += "🔐 Email + Password:\n" + "\n".join([f"{e[0]}|{e[1]}" for e in pw_emails])
            await query.edit_message_text(f"📤 **{product_name}**\n\n{content[:2000]}")
        return

# =================================================================================
# ADMIN: BLOCK/UNBLOCK CALLBACKS
# =================================================================================

async def block_unblock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        return
    
    data = query.data
    
    if data == "block_menu":
        context.user_data["awaiting_block_user"] = True
        await query.edit_message_text("🚫 Enter User ID to block:\n/cancel to abort")
        return
    
    if data == "unblock_menu":
        context.user_data["awaiting_unblock_user"] = True
        await query.edit_message_text("✅ Enter User ID to unblock:\n/cancel to abort")
        return
    
    if data == "blocked_list":
        if not blocked_users:
            await query.edit_message_text("✅ No blocked users!")
            return
        msg = "🚫 **BLOCKED USERS**\n\n"
        for uid in blocked_users:
            msg += f"🆔 {uid}\n"
        await query.edit_message_text(msg, parse_mode='HTML')
        return

# =================================================================================
# PHOTO HANDLER
# =================================================================================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo_id = update.message.photo[-1].file_id
    caption = update.message.caption or ""
    
    # User support with screenshot
    if user_support_mode.get(user_id):
        cursor.execute("INSERT INTO support_messages (user_id, message, screenshot_id, timestamp) VALUES (?, ?, ?, ?)",
                       (user_id, caption or "Screenshot only", photo_id, datetime.datetime.now().isoformat()))
        conn.commit()
        try:
            await context.bot.send_photo(ADMIN_ID, photo_id, caption=f"💬 **SUPPORT WITH SCREENSHOT**\n\n👤 User: {user_id}\n📝 {caption[:200]}", parse_mode='HTML')
        except:
            pass
        await update.message.reply_text("✅ Screenshot sent to support!")
        return
    
    # User report with screenshot
    if context.user_data.get("awaiting_report"):
        context.user_data["report_screenshot"] = photo_id
        context.user_data["report_desc"] = context.user_data.get("report_desc", "") + " " + caption
        await update.message.reply_text(
            "📸 Screenshot saved! Continue sending description or click SUBMIT.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 SUBMIT REPORT", callback_data="report_submit")]])
        )
        return
    
    # Payment proof
    if context.user_data.get("awaiting_proof"):
        if user_id in blocked_users:
            await update.message.reply_text("❌ You are blocked!")
            return
        
        now = time.time()
        if user_id not in fraud_tracker:
            fraud_tracker[user_id] = {"last": 0, "count": 0}
        
        if now - fraud_tracker[user_id]["last"] < 60:
            await update.message.reply_text("⏳ Please wait 60 seconds between submissions")
            return
        
        fraud_tracker[user_id]["last"] = now
        fraud_tracker[user_id]["count"] += 1
        
        if fraud_tracker[user_id]["count"] >= 5:
            blocked_users.add(user_id)
            ban_user(user_id)
            await update.message.reply_text("❌ You have been blocked for suspicious activity!")
            return
        
        sender_name = context.user_data.get("sender_name", "Unknown")
        ref = context.user_data.get("payment_ref", generate_ref())
        
        try:
            cursor.execute("INSERT INTO deposits (user_id, sender_name, ref, status) VALUES (?, ?, ?, 'pending')",
                           (user_id, sender_name, ref))
            conn.commit()
            
            pending_approvals[user_id] = {
                "sender_name": sender_name,
                "photo_id": photo_id,
                "ref": ref,
                "username": update.message.from_user.username,
                "full_name": update.message.from_user.full_name
            }
            
            kb = [
                [InlineKeyboardButton("✅ Approve", callback_data=f"approve:{user_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"reject:{user_id}")]
            ]
            await context.bot.send_photo(
                ADMIN_ID,
                photo_id,
                caption=f"💳 **NEW DEPOSIT**\n\n"
                        f"👤 {update.message.from_user.full_name}\n"
                        f"📛 @{update.message.from_user.username or 'N/A'}\n"
                        f"🆔 {user_id}\n"
                        f"🏦 {sender_name}\n"
                        f"🔢 {ref}",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode='HTML'
            )
            
            await update.message.reply_text("✅ Payment proof submitted! Awaiting admin approval.")
            context.user_data["awaiting_proof"] = False
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            context.user_data["awaiting_proof"] = False
        return
    
    # Admin broadcast with photo
    if is_admin(user_id) and context.user_data.get("awaiting_broadcast"):
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        if not users:
            await update.message.reply_text("❌ No users!")
            context.user_data.pop("awaiting_broadcast", None)
            return
        
        sent = 0
        failed = 0
        status_msg = await update.message.reply_text(f"📢 Broadcasting image to {len(users)} users...")
        
        for (uid,) in users:
            try:
                await context.bot.send_photo(uid, photo_id, caption=caption or "📢 Admin Broadcast!")
                sent += 1
            except:
                failed += 1
            time.sleep(0.05)
        
        await status_msg.edit_text(
            f"✅ **IMAGE BROADCAST COMPLETE!**\n\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}",
            parse_mode='HTML'
        )
        context.user_data.pop("awaiting_broadcast", None)
        return
    
    # Admin restock file
    if is_admin(user_id) and context.user_data.get("awaiting_restock_file"):
        await handle_restock_file(update, context)
        return
    
    await update.message.reply_text("❌ Not expecting a photo here.")

# =================================================================================
# RESTOCK FILE HANDLER
# =================================================================================

async def handle_restock_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    if not context.user_data.get("awaiting_restock_file"):
        return
    
    product_name = context.user_data.get("restock_product")
    if not product_name:
        return
    
    try:
        file = await update.message.document.get_file()
        content = await file.download_as_bytearray()
        text = content.decode('utf-8', errors='ignore')
        
        # Parse each line
        email_only = []
        with_password = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if '|' in line:
                # Email + Password
                parts = line.split('|', 1)
                email = parts[0].strip()
                password = parts[1].strip()
                if email and '@' in email and password:
                    with_password.append((email, password))
                    print(f"✅ Added with password: {email}")
            else:
                # Email only
                if line and '@' in line:
                    email_only.append(line)
                    print(f"✅ Added email only: {line}")
        
        if not email_only and not with_password:
            await update.message.reply_text(
                "❌ No valid emails found!\n\n"
                "📧 For Email Only: `email@gmail.com`\n"
                "🔐 For Email + Password: `email@gmail.com|password`\n\n"
                "Example:\n"
                "`user1@gmail.com`\n"
                "`user2@gmail.com|pass123`",
                parse_mode='Markdown'
            )
            return
        
        # Add email only items
        added_email_only = 0
        for email in email_only:
            if add_ig_stock(product_name, email, user_id, password=None):
                added_email_only += 1
        
        # Add with password items
        added_with_password = 0
        for email, password in with_password:
            if add_ig_stock(product_name, email, user_id, password=password):
                added_with_password += 1
        
        await update.message.reply_text(
            f"✅ **RESTOCK COMPLETE!**\n\n"
            f"📦 {product_name} followers\n"
            f"📧 Email Only: +{added_email_only} (Total: {get_ig_stock_count(product_name, require_password=False)})\n"
            f"🔐 Email + Password: +{added_with_password} (Total: {get_ig_stock_count(product_name, require_password=True)})\n"
            f"📊 Total stock: {get_ig_stock_count(product_name, require_password=False) + get_ig_stock_count(product_name, require_password=True)}",
            parse_mode='HTML'
        )
        
        # Log restock
        cursor.execute("INSERT INTO restock_logs (admin_id, product_name, quantity) VALUES (?, ?, ?)",
                       (user_id, product_name, added_email_only + added_with_password))
        conn.commit()
        
        context.user_data["awaiting_restock_file"] = False
        context.user_data["restock_product"] = None
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


# =================================================================================
# RESTOCK TEXT HANDLER (NEW - For pasting emails directly)
# =================================================================================

async def handle_restock_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle restock via direct text input (not file)"""
    user_id = update.message.from_user.id
    if not is_admin(user_id):
        return
    
    if not context.user_data.get("awaiting_restock_file"):
        return
    
    product_name = context.user_data.get("restock_product")
    if not product_name:
        return
    
    text = update.message.text.strip()
    
    try:
        # Parse each line
        email_only = []
        with_password = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if '|' in line:
                # Email + Password
                parts = line.split('|', 1)
                email = parts[0].strip()
                password = parts[1].strip()
                if email and '@' in email and password:
                    with_password.append((email, password))
                    print(f"✅ Added with password: {email}")
            else:
                # Email only
                if line and '@' in line:
                    email_only.append(line)
                    print(f"✅ Added email only: {line}")
        
        if not email_only and not with_password:
            await update.message.reply_text(
                "❌ No valid emails found!\n\n"
                "📧 For Email Only: `email@gmail.com`\n"
                "🔐 For Email + Password: `email@gmail.com|password`\n\n"
                "Example:\n"
                "`user1@gmail.com`\n"
                "`user2@gmail.com|pass123`",
                parse_mode='Markdown'
            )
            return
        
        # Add email only items
        added_email_only = 0
        for email in email_only:
            if add_ig_stock(product_name, email, user_id, password=None):
                added_email_only += 1
        
        # Add with password items
        added_with_password = 0
        for email, password in with_password:
            if add_ig_stock(product_name, email, user_id, password=password):
                added_with_password += 1
        
        await update.message.reply_text(
            f"✅ **RESTOCK COMPLETE!**\n\n"
            f"📦 {product_name} followers\n"
            f"📧 Email Only: +{added_email_only} (Total: {get_ig_stock_count(product_name, require_password=False)})\n"
            f"🔐 Email + Password: +{added_with_password} (Total: {get_ig_stock_count(product_name, require_password=True)})\n"
            f"📊 Total stock: {get_ig_stock_count(product_name, require_password=False) + get_ig_stock_count(product_name, require_password=True)}",
            parse_mode='HTML'
        )
        
        # Log restock
        cursor.execute("INSERT INTO restock_logs (admin_id, product_name, quantity) VALUES (?, ?, ?)",
                       (user_id, product_name, added_email_only + added_with_password))
        conn.commit()
        
        context.user_data["awaiting_restock_file"] = False
        context.user_data["restock_product"] = None
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# =================================================================================
# TEXT HANDLER
# =================================================================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Check banned
    if is_banned(user_id):
        await update.message.reply_text("🚫 You are banned!")
        return
    
    # Support mode
    if user_support_mode.get(user_id):
        await handle_support_message(update, context)
        return
    
    # Report description
    if context.user_data.get("awaiting_report"):
        current = context.user_data.get("report_desc", "")
        context.user_data["report_desc"] = (current + " " + text).strip()
        await update.message.reply_text(
            "✅ Text added! Send more or click Submit.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 SUBMIT REPORT", callback_data="report_submit")]])
        )
        return
    
    # Funding flow
    if context.user_data.get("awaiting_name"):
        context.user_data["sender_name"] = text
        context.user_data["awaiting_name"] = False
        context.user_data["awaiting_proof"] = True
        await update.message.reply_text("📸 Now send SCREENSHOT of your payment.")
        return
    
    # ===== ADMIN TEXT HANDLERS =====
    if is_admin(user_id):
        # ===== RESTOCK VIA TEXT (NEW) =====
        if context.user_data.get("awaiting_restock_file"):
            await handle_restock_text(update, context)
            return
        
        # Add funds
        if context.user_data.get("awaiting_addfund_user"):
            try:
                target_id = int(text)
                context.user_data["addfund_target"] = target_id
                context.user_data["awaiting_addfund_user"] = False
                context.user_data["awaiting_addfund_amount"] = True
                await update.message.reply_text(
                    f"💰 User: {target_id}\n"
                    f"Current Balance: ₦{get_balance(target_id)}\n\n"
                    f"Enter amount to add:\n/back to abort",
                    parse_mode='HTML'
                )
                return
            except:
                await update.message.reply_text("❌ Invalid ID!")
                return
        
        if context.user_data.get("awaiting_addfund_amount"):
            try:
                amount = int(text)
                target_id = context.user_data.get("addfund_target")
                if not target_id:
                    return
                old_bal = get_balance(target_id)
                update_wallet(target_id, amount)
                log_transaction(target_id, "credit", amount, "admin_addfund")
                await update.message.reply_text(
                    f"✅ Added ₦{amount} to user {target_id}\n"
                    f"💰 {old_bal} → {get_balance(target_id)}",
                    parse_mode='HTML'
                )
                context.user_data.pop("addfund_target", None)
                context.user_data.pop("awaiting_addfund_amount", None)
                return
            except:
                await update.message.reply_text("❌ Invalid amount!")
                return
        
        # Deduct funds
        if context.user_data.get("awaiting_deduct_user"):
            try:
                target_id = int(text)
                context.user_data["deduct_target"] = target_id
                context.user_data["awaiting_deduct_user"] = False
                context.user_data["awaiting_deduct_amount"] = True
                await update.message.reply_text(
                    f"💸 User: {target_id}\n"
                    f"Current Balance: ₦{get_balance(target_id)}\n\n"
                    f"Enter amount to deduct:\n/back to abort",
                    parse_mode='HTML'
                )
                return
            except:
                await update.message.reply_text("❌ Invalid ID!")
                return
        
        if context.user_data.get("awaiting_deduct_amount"):
            try:
                amount = int(text)
                target_id = context.user_data.get("deduct_target")
                if not target_id:
                    return
                bal = get_balance(target_id)
                if bal < amount:
                    await update.message.reply_text(f"❌ User only has ₦{bal}!")
                    return
                update_wallet(target_id, -amount)
                log_transaction(target_id, "debit", amount, "admin_deduct")
                await update.message.reply_text(
                    f"✅ Deducted ₦{amount} from user {target_id}\n"
                    f"💰 {bal} → {get_balance(target_id)}",
                    parse_mode='HTML'
                )
                context.user_data.pop("deduct_target", None)
                context.user_data.pop("awaiting_deduct_amount", None)
                return
            except:
                await update.message.reply_text("❌ Invalid amount!")
                return
        
        # View balance
        if context.user_data.get("awaiting_view_balance"):
            try:
                target_id = int(text)
                bal = get_balance(target_id)
                await update.message.reply_text(
                    f"👤 **User Balance**\n\n"
                    f"🆔 ID: {target_id}\n"
                    f"💰 Balance: ₦{bal}",
                    parse_mode='HTML'
                )
                context.user_data.pop("awaiting_view_balance", None)
                return
            except:
                await update.message.reply_text("❌ Invalid ID!")
                return
        
        # Message user
        if context.user_data.get("awaiting_msg_user"):
            try:
                target_id = int(text)
                context.user_data["msg_target"] = target_id
                context.user_data["awaiting_msg_user"] = False
                context.user_data["awaiting_msg_text"] = True
                await update.message.reply_text(
                    f"💬 User: {target_id}\n\n"
                    f"Send your message:\n/back to abort",
                    parse_mode='HTML'
                )
                return
            except:
                await update.message.reply_text("❌ Invalid ID!")
                return
        
        if context.user_data.get("awaiting_msg_text"):
            target_id = context.user_data.get("msg_target")
            if target_id:
                try:
                    await context.bot.send_message(target_id, f"📬 **Message from Admin:**\n\n{text}")
                    await update.message.reply_text(f"✅ Sent to {target_id}!")
                except:
                    await update.message.reply_text(f"❌ Failed to send to {target_id}")
            context.user_data.pop("msg_target", None)
            context.user_data.pop("awaiting_msg_text", None)
            return
        
        # Broadcast
        if context.user_data.get("awaiting_broadcast"):
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            if not users:
                await update.message.reply_text("❌ No users!")
                context.user_data.pop("awaiting_broadcast", None)
                return
            
            sent = 0
            failed = 0
            status_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
            
            for (uid,) in users:
                try:
                    await context.bot.send_message(uid, f"📢 {text}")
                    sent += 1
                except:
                    failed += 1
                time.sleep(0.05)
            
            await status_msg.edit_text(
                f"✅ **BROADCAST COMPLETE!**\n\n"
                f"✅ Sent: {sent}\n"
                f"❌ Failed: {failed}",
                parse_mode='HTML'
            )
            
            # Log broadcast
            cursor.execute("INSERT INTO broadcast_logs (admin_id, message, total_sent, total_failed) VALUES (?, ?, ?, ?)",
                           (user_id, text[:500], sent, failed))
            conn.commit()
            
            context.user_data.pop("awaiting_broadcast", None)
            return
        
        # Approve deposit amount
        if context.user_data.get("approving_user"):
            try:
                amount = int(text)
                target_id = context.user_data.pop("approving_user")
                
                if target_id not in pending_approvals:
                    await update.message.reply_text("⚠️ Already processed!")
                    return
                
                info = pending_approvals[target_id]
                old_bal = get_balance(target_id)
                update_wallet(target_id, amount)
                cursor.execute("UPDATE deposits SET amount=?, status='approved' WHERE ref=?", (amount, info.get('ref')))
                conn.commit()
                log_transaction(target_id, "credit", amount, "deposit_approved")
                new_bal = get_balance(target_id)
                
                try:
                    await context.bot.send_message(
                        target_id,
                        f"✅ **PAYMENT APPROVED!**\n\n"
                        f"💰 Amount: ₦{amount}\n"
                        f"💳 Previous: ₦{old_bal}\n"
                        f"💳 New: ₦{new_bal}\n\n"
                        f"Thank you! You can now purchase products.",
                        parse_mode='HTML'
                    )
                except:
                    pass
                
                await update.message.reply_text(
                    f"✅ Approved ₦{amount} for user {target_id}\n"
                    f"💳 {old_bal} → {new_bal}",
                    parse_mode='HTML'
                )
                pending_approvals.pop(target_id, None)
                return
            except:
                await update.message.reply_text("❌ Invalid amount! Send a number.")
                return
        
        # Decline deposit reason
        if context.user_data.get("declining_user"):
            target_id = context.user_data.pop("declining_user")
            reason = text
            
            if target_id in pending_approvals:
                info = pending_approvals[target_id]
                cursor.execute("UPDATE deposits SET status='rejected', decline_reason=? WHERE ref=?", (reason, info.get('ref')))
                conn.commit()
                
                try:
                    await context.bot.send_message(
                        target_id,
                        f"❌ **PAYMENT DECLINED**\n\n"
                        f"📋 Reason: {reason}\n\n"
                        f"Please fix and try again.",
                        parse_mode='HTML'
                    )
                except:
                    pass
                
                await update.message.reply_text(f"✅ Declined user {target_id}: {reason}")
                pending_approvals.pop(target_id, None)
            return
        
        # Reply to report
        if context.user_data.get("replying_to"):
            report_id = context.user_data.pop("replying_to")
            reply = text
            
            cursor.execute("SELECT user_id FROM reports WHERE id=?", (report_id,))
            r = cursor.fetchone()
            
            if r:
                try:
                    await context.bot.send_message(r[0], f"📬 **Admin Response (#{report_id})**\n\n{reply}")
                except:
                    pass
                
                cursor.execute("UPDATE reports SET admin_response=? WHERE id=?", (reply, report_id))
                conn.commit()
                
                await update.message.reply_text(f"✅ Reply sent to report #{report_id}!")
            return
        
        # Block/Unblock
        if context.user_data.get("awaiting_block_user"):
            try:
                target_id = int(text)
                if target_id in blocked_users:
                    await update.message.reply_text(f"ℹ️ Already blocked!")
                else:
                    blocked_users.add(target_id)
                    ban_user(target_id)
                    await update.message.reply_text(f"🚫 User {target_id} blocked!")
                    try:
                        await context.bot.send_message(target_id, "🚫 You have been blocked!")
                    except:
                        pass
            except:
                await update.message.reply_text("❌ Invalid ID!")
            context.user_data.pop("awaiting_block_user", None)
            return
        
        if context.user_data.get("awaiting_unblock_user"):
            try:
                target_id = int(text)
                if target_id not in blocked_users:
                    await update.message.reply_text(f"ℹ️ Not blocked!")
                else:
                    blocked_users.discard(target_id)
                    unban_user(target_id)
                    await update.message.reply_text(f"✅ User {target_id} unblocked!")
                    try:
                        await context.bot.send_message(target_id, "✅ You have been unblocked!")
                    except:
                        pass
            except:
                await update.message.reply_text("❌ Invalid ID!")
            context.user_data.pop("awaiting_unblock_user", None)
            return
    
    # ... rest of code (menu buttons, etc.)
    
    # ===== MENU BUTTONS =====
    if text == "💰 Wallet":
        await wallet(update, context)
        return
    
    if text == "➕ Fund Wallet":
        await fund(update, context)
        return
    
    if text == "📦 Check Stock":
        await user_stock(update, context)
        return
    
    if text == "🧾 My History":
        await history(update, context)
        return
    
    if text == "💳 My Deposits":
        await my_deposits(update, context)
        return
    
    if text == "🛒 Buy Products":
        await buy_products_menu(update, context)
        return
    
    if text == "🛒 My Cart":
        await view_cart(update, context)
        return
    
    if text == "🤖 Expert Support":
        await expert_support(update, context)
        return
    
    if text == "📝 Report Issue":
        await report_issue(update, context)
        return
    
    if text == "🤝 Refer & Earn":
        await refer_earn_menu(update, context)
        return
    
    if text == "📋 Help & FAQ":
        await help_faq(update, context)
        return
    
    if text == "❌ Exit Support":
        user_support_mode.pop(user_id, None)
        await start(update, context)
        return
    
    if text == "👑 Admin Panel" and is_admin(user_id):
        await admin_panel(update, context)
        return
    
    # Admin panel buttons
    if is_admin(user_id):
        if text == "📊 Stats":
            await admin_stats(update, context)
            return
        
        if text == "📥 Pending":
            await admin_pending_deposits(update, context)
            return
        
        if text == "📝 Reports":
            await admin_reports(update, context)
            return
        
        if text == "💰 Add Funds":
            await admin_add_funds_start(update, context)
            return
        
        if text == "💸 Deduct Funds":
            await admin_deduct_funds_start(update, context)
            return
        
        if text == "📈 Sales":
            await admin_sales(update, context)
            return
        
        if text == "📦 Restock":
            await admin_restock_menu(update, context)
            return
        
        if text == "📢 Broadcast":
            await admin_broadcast(update, context)
            return
        
        if text == "💬 Message User":
            await admin_message_user_start(update, context)
            return
        
        if text == "👤 View Balance":
            await admin_view_balance_start(update, context)
            return
        
        if text == "🚫 Block/Unblock":
            await admin_block_unblock_menu(update, context)
            return
        
        if text == "🗑 Clear Stock":
            await admin_clear_stock_menu(update, context)
            return
        
        if text == "📤 Extract Stock":
            await admin_extract_stock_menu(update, context)
            return
        
        if text == "🔄 User Menu":
            await start(update, context)
            return
    
    await update.message.reply_text("❓ Unknown command. Use the menu buttons.")

# =================================================================================
# WITHDRAW COMMAND
# =================================================================================

async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if is_banned(user_id):
        await update.message.reply_text("🚫 You are banned!")
        return
    
    bal = get_balance(user_id)
    if bal < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"❌ Minimum withdrawal: ₦{MIN_WITHDRAWAL}\nYour balance: ₦{bal}",
            parse_mode='HTML'
        )
        return
    
    await update.message.reply_text(
        f"📤 **WITHDRAWAL REQUEST**\n\n"
        f"Your balance: ₦{bal}\n"
        f"Minimum: ₦{MIN_WITHDRAWAL}\n\n"
        f"Send in format:\n"
        f"`AMOUNT|BANK|ACCOUNT|NAME`\n\n"
        f"Example:\n"
        f"`5000|OPay|9032741650|John Doe`\n\n"
        f"Type /cancel to cancel.",
        parse_mode='Markdown'
    )
    context.user_data["awaiting_withdraw"] = True

async def process_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    if not context.user_data.get("awaiting_withdraw"):
        return
    
    if text == "/cancel":
        context.user_data.pop("awaiting_withdraw", None)
        await update.message.reply_text("❌ Withdrawal cancelled!")
        return
    
    parts = text.split('|')
    if len(parts) != 4:
        await update.message.reply_text("❌ Invalid format!\nUse: AMOUNT|BANK|ACCOUNT|NAME")
        return
    
    try:
        amount = int(parts[0].strip())
        bank = parts[1].strip()
        account = parts[2].strip()
        name = parts[3].strip()
        
        if amount < MIN_WITHDRAWAL:
            await update.message.reply_text(f"❌ Minimum: ₦{MIN_WITHDRAWAL}")
            return
        
        bal = get_balance(user_id)
        if amount > bal:
            await update.message.reply_text(f"❌ Insufficient! Balance: ₦{bal}")
            return
        
        update_wallet(user_id, -amount)
        log_transaction(user_id, "debit", amount, f"withdrawal_to_{bank}")
        
        await context.bot.send_message(
            ADMIN_ID,
            f"📤 **WITHDRAWAL REQUEST**\n\n"
            f"👤 User: {user_id}\n"
            f"💰 Amount: ₦{amount}\n"
            f"🏦 Bank: {bank}\n"
            f"📋 Account: {account}\n"
            f"👤 Name: {name}",
            parse_mode='HTML'
        )
        
        await update.message.reply_text(
            f"✅ **WITHDRAWAL REQUEST SUBMITTED!**\n\n"
            f"💰 Amount: ₦{amount}\n"
            f"🏦 Bank: {bank}\n\n"
            f"⏳ Admin will process within 24 hours.",
            parse_mode='HTML'
        )
        
        context.user_data.pop("awaiting_withdraw", None)
        
    except:
        await update.message.reply_text("❌ Invalid amount!")

# =================================================================================
# CANCEL COMMAND
# =================================================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for key in list(context.user_data.keys()):
        del context.user_data[key]
    await update.message.reply_text("❌ All operations cancelled")

# =================================================================================
# CALLBACK HANDLER
# =================================================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # Back to main
    if data == "back_main":
        await query.message.delete()
        await start(update, context)
        return
    
    # Payment
    if data.startswith("pay:"):
        ref = data.split(":")[1]
        context.user_data["payment_ref"] = ref
        context.user_data["awaiting_name"] = True
        await query.edit_message_text(f"💳 REF: {ref}\n\n📝 Send SENDER NAME.\n/back to cancel")
        return
    
    # IG Buy
    if data.startswith("buy_"):
        await buy_product_callback(update, context)
        return
    
    if data.startswith("confirm_"):
        await confirm_purchase_callback(update, context)
        return
    
    # IG Cart
    if data.startswith("addcart_") or data.startswith("rmcart_") or data.startswith("qtyadd_") or data.startswith("qtysub_") or data in ["clearcart", "checkout"]:
        await cart_callback(update, context)
        return
    
    # IG Categories
    if data.startswith("cat_") or data == "back_to_categories":
        if data == "back_to_categories":
            await back_to_categories(update, context)
        else:
            await product_category_callback(update, context)
        return
    
    # Reports
    if data.startswith("report_"):
        if data in ["report_submit", "report_cancel"]:
            await report_submit_callback(update, context)
        else:
            await report_callback(update, context)
        return
    
    # FAQ
    if data.startswith("faq_"):
        if data == "faq_back":
            await faq_back(update, context)
        else:
            await faq_callback(update, context)
        return
    
    # Admin - Resolve/Reply/AddFund
    if data.startswith("resolve_"):
        report_id = int(data.replace("resolve_", ""))
        cursor.execute("UPDATE reports SET status='resolved' WHERE id=?", (report_id,))
        cursor.execute("SELECT user_id FROM reports WHERE id=?", (report_id,))
        r = cursor.fetchone()
        conn.commit()
        if r:
            try:
                await context.bot.send_message(r[0], f"✅ Your report #{report_id} has been resolved!")
            except:
                pass
        await query.edit_message_text(f"✅ Report #{report_id} resolved!")
        return
    
    if data.startswith("reply_"):
        report_id = int(data.replace("reply_", ""))
        context.user_data["replying_to"] = report_id
        await query.edit_message_text(
            f"💬 **REPLY TO REPORT #{report_id}**\n\nSend your reply message:\n/back to abort",
            parse_mode='HTML'
        )
        return
    
    if data.startswith("addfund_"):
        target_id = int(data.replace("addfund_", ""))
        context.user_data["addfund_target"] = target_id
        await query.edit_message_text(
            f"💰 **ADD FUNDS**\n\nUser: {target_id}\nCurrent Balance: ₦{get_balance(target_id)}\n\nSend amount to add:\n/back to abort",
            parse_mode='HTML'
        )
        return
    
    # Admin - Approve/Reject
    if data.startswith("approve:"):
        target_id = int(data.replace("approve:", ""))
        if target_id not in pending_approvals:
            await query.answer("⚠️ Already processed!", show_alert=True)
            return
        context.user_data["approving_user"] = target_id
        await query.edit_message_text(
            f"💰 **APPROVE DEPOSIT**\n\nUser: {target_id}\n\nSend amount (e.g., 5000):\n/back to abort",
            parse_mode='HTML'
        )
        return
    
    if data.startswith("reject:"):
        target_id = int(data.replace("reject:", ""))
        if target_id not in pending_approvals:
            await query.answer("⚠️ Already processed!", show_alert=True)
            return
        context.user_data["declining_user"] = target_id
        await query.edit_message_text(
            f"❌ **DECLINE DEPOSIT**\n\nUser: {target_id}\n\nSend decline reason:\n/back to abort",
            parse_mode='HTML'
        )
        return
    
    # Admin - Restock
    if data.startswith("restock_"):
        await restock_callback(update, context)
        return
    
    # Admin - Clear Stock
    if data.startswith("clearstock_"):
        await clear_stock_callback(update, context)
        return
    
    # Admin - Extract Stock
    if data.startswith("extract_"):
        await extract_stock_callback(update, context)
        return
    
    # Admin - Block/Unblock
    if data in ["block_menu", "unblock_menu", "blocked_list"]:
        await block_unblock_callback(update, context)
        return
    
    # Admin - Back to admin
    if data == "back_to_admin":
        await admin_panel(update, context)
        return

# =================================================================================
# MAIN
# =================================================================================

def main():
    # Create application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("withdraw", withdraw_command))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_photo))
    
    print("="*60)
    print("📱 IG SHOP BOT RUNNING!")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"🤖 Bot: @{BOT_USERNAME}")
    print("="*60)
    print("📱 FEATURES:")
    print("   • Email Only accounts")
    print("   • Email + Password accounts (+₦500)")
    print("   • Cart system for bulk purchases")
    print("   • Complete admin panel")
    print("   • Stock management (restock, clear, extract)")
    print("   • Admin can add email+password manually")
    print("="*60)
    print("🚀 BOT RUNNING...")
    print("="*60)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
