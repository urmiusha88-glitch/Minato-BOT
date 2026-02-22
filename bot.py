import logging
import psycopg2
import random
import string
import os
import re
import httpx
from datetime import date
from faker import Faker
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# ======================================================
# 👇 CONFIGURATION SECTION (MUST EDIT THIS)
# ======================================================
TOKEN = "8290942305:AAGB70nqTwvapZIaBCeXxIwnwUnGpq_ccHc"  # ⚠️ এখানে BotFather থেকে পাওয়া নতুন টোকেনটি বসান
ADMIN_ID = 6198703244  # Your Telegram ID (MAIN OWNER)

# 💰 PAYMENT DETAILS
BKASH_NUMBER = "01846849460"    
NAGAD_NUMBER = "01846849460"    
BINANCE_PAY_ID = "1016246479"  

# 🗄️ DATABASE URL (RAILWAY POSTGRESQL LINK)
DB_URL = "postgresql://postgres:cIJaXIJvmBepjzPcXskiJgFPwvkLdlEA@maglev.proxy.rlwy.net:22522/railway"

# 🔴 GROUP & CHANNEL IDS
ADMIN_LOG_ID = -1003769033152
PUBLIC_LOG_ID = -1003775622081

# ⚠️ Force Join Channel
CHANNEL_ID = "@minatologs"
CHANNEL_INVITE_LINK = "https://t.me/minatologs/2"

# ======================================================
FB_ID_LINK ="https://www.facebook.com/yours.ononto"
FB_PAGE_LINK = "https://www.facebook.com/toxicnaaa69"
# ======================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- COUNTRY CALLING CODES ---
COUNTRY_CALLING_CODES = {
    "US": "+1", "GB": "+44", "CA": "+1", "AU": "+61", "IN": "+91", "BD": "+880",
    "BR": "+55", "FR": "+33", "DE": "+49", "IT": "+39", "ES": "+34", "MX": "+52",
    "JP": "+81", "CN": "+86", "RU": "+7", "ZA": "+27", "NG": "+234", "AR": "+54",
    "CO": "+57", "PE": "+51", "PH": "+63", "VN": "+84", "TH": "+66", "MY": "+60",
    "ID": "+62", "PK": "+92", "TR": "+90", "EG": "+20", "SA": "+966", "AE": "+971",
    "KR": "+82", "SG": "+65", "SE": "+46", "CH": "+41", "NL": "+31", "PL": "+48"
}

# --- DATABASE CONNECTION HELPER ---
def get_db_connection():
    return psycopg2.connect(DB_URL)

# --- INIT DATABASE ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id BIGINT PRIMARY KEY, credits INTEGER, role TEXT, generated_count INTEGER DEFAULT 0, full_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ccs_normal 
                 (id SERIAL PRIMARY KEY, cc_info TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ccs_hq 
                 (id SERIAL PRIMARY KEY, cc_info TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS codes 
                 (code TEXT PRIMARY KEY, credit_amount INTEGER, role_reward TEXT, is_redeemed INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins 
                 (admin_id BIGINT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bonus 
                 (user_id BIGINT PRIMARY KEY, last_claim DATE)''') # NEW TABLE FOR BONUS
    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE admin_id=%s", (user_id,))
    res = c.fetchone()
    conn.close()
    return bool(res)

def get_user(user_id, first_name="Unknown"):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, credits, role, generated_count, full_name) VALUES (%s, %s, %s, 0, %s)", (user_id, 0, 'Free', first_name))
        conn.commit()
        user = (user_id, 0, 'Free', 0, first_name)
    else:
        if first_name != "Unknown":
            c.execute("UPDATE users SET full_name=%s WHERE user_id=%s", (first_name, user_id))
            conn.commit()
    conn.close()
    return user

def generate_minato_code(role_tag="PREMIUM"):
    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"MINATO-{part1}-{part2}-{role_tag.upper()}"

async def check_join(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['left', 'kicked']: return False
        return True
    except: 
        return True 

def generate_fake_identity(country_code):
    cc = country_code.upper()
    base_fake = Faker('en_US') 
    
    try:
        local_fake = Faker(f"en_{cc}")
    except:
        try:
            local_fake = Faker(f"{country_code.lower()}_{cc}")
        except:
            local_fake = Faker('en_US')
            
    try:
        state = local_fake.state()
    except:
        try:
            state = local_fake.city()
        except:
            state = "State/Province"

    c_code = COUNTRY_CALLING_CODES.get(cc, "+1") 
    num = ''.join([str(random.randint(0,9)) for _ in range(10)])
    phone_number = f"{c_code} {num[:3]}-{num[3:6]}-{num[6:]}"

    return {
        "name": base_fake.name(),
        "street": local_fake.street_address(),
        "state": state,
        "zipcode": local_fake.postcode(),
        "phone": phone_number,
        "ip": base_fake.ipv4_public()
    }

# --- HANDLERS ---

# 1. NEW MAIN MENU UI
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await check_join(user.id, context):
        await update.message.reply_text(
            f"❌ **ACCESS DENIED**\n\n⚠️ You must join our official channel to use this bot.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Join Channel First", url=CHANNEL_INVITE_LINK)]])
        )
        return

    db_user = get_user(user.id, user.first_name)
    
    welcome_text = (
        f"🔥 **𝐌𝐈𝐍𝐀𝐓𝐎 𝐂𝐂 𝐒𝐓𝐎𝐑𝐄** 🔥\n"
        f"▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱\n"
        f"👋 **Welcome, {user.first_name}!**\n\n"
        f"👤 **𝐀𝐜𝐜𝐨𝐮𝐧𝐭 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧:**\n"
        f"├ 🆔 **ID:** `{user.id}`\n"
        f"├ 💎 **Credits:** `{db_user[1]}`\n"
        f"├ 👑 **Role:** `{db_user[2]}`\n"
        f"└ 📦 **Purchases:** `{db_user[3]}`\n\n"
        f"🎁 **Tips:** Click 'Daily Bonus' for free credits!\n"
        f"▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Open Store (Generate)", callback_data='store_menu')],
        [InlineKeyboardButton("💰 Deposit", callback_data='deposit_info'), InlineKeyboardButton("🎁 Daily Bonus", callback_data='daily_bonus')],
        [InlineKeyboardButton("🎫 Redeem Code", callback_data='redeem_btn')],
        [InlineKeyboardButton("👨‍💻 Admin Support", url=f"tg://user?id={ADMIN_ID}")] 
    ]
    
    if update.message: await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else: 
        try: await update.callback_query.message.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except: pass

# 2. NEW STORE MENU
async def store_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛒 **𝐌𝐈𝐍𝐀𝐓𝐎 𝐒𝐓𝐎𝐑𝐄**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Please select the quality of the CC you want to generate. "
        "HQ CCs have a higher valid rate.\n\n"
        "🟢 **Normal CC:** 100 Credits\n"
        "🟣 **High Quality (HQ) CC:** 250 Credits"
    )
    kb = [
        [InlineKeyboardButton("🟢 Gen Normal CC (100 Cr)", callback_data='gen_normal')],
        [InlineKeyboardButton("🟣 Gen HQ CC (250 Cr)", callback_data='gen_hq')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]
    ]
    await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

# 3. DAILY BONUS FUNCTION
async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not await check_join(user_id, context):
        await query.answer("❌ Join Channel First!", show_alert=True)
        return

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT last_claim FROM bonus WHERE user_id=%s", (user_id,))
    res = c.fetchone()
    today = date.today()
    
    if res and res[0] == today:
        await query.answer("❌ You already claimed your bonus today! Come back tomorrow.", show_alert=True)
    else:
        bonus_amount = random.randint(15, 50)
        c.execute("UPDATE users SET credits = credits + %s WHERE user_id=%s", (bonus_amount, user_id))
        if res:
            c.execute("UPDATE bonus SET last_claim=%s WHERE user_id=%s", (today, user_id))
        else:
            c.execute("INSERT INTO bonus (user_id, last_claim) VALUES (%s, %s)", (user_id, today))
        conn.commit()
        await query.answer(f"🎉 Awesome! You received {bonus_amount} Free Credits today!", show_alert=True)
        
    conn.close()
    await start(update, context)

# 4. GENERATE CC (NO BALANCE, EXACT FORMAT)
async def generate_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    if not await check_join(user_id, context):
        await query.answer("❌ Join Channel First!", show_alert=True)
        return

    db_user = get_user(user_id)
    
    if data == 'gen_normal':
        COST = 100
        table = 'ccs_normal'
        q_text = "NORMAL"
    elif data == 'gen_hq':
        COST = 250
        table = 'ccs_hq'
        q_text = "HIGH QUALITY"
    else:
        return

    if db_user[1] < COST:
        await query.answer(f"❌ Low Balance! Need {COST} Credits for {q_text} CC.", show_alert=True)
        return

    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute(f"SELECT id, cc_info FROM {table} ORDER BY RANDOM() LIMIT 1")
    account = c.fetchone()
    
    if account:
        c.execute("UPDATE users SET credits = credits - %s, generated_count = generated_count + 1 WHERE user_id=%s", (COST, user_id))
        c.execute(f"DELETE FROM {table} WHERE id=%s", (account[0],))
        conn.commit()
        
        cc_full_text = account[1]
        cc_number = cc_full_text.split('|')[0]
        bin_num = cc_number[:6]
        
        await query.message.edit_text(f"⏳ **Generating {q_text} CC... Checking BIN & Identity...**", parse_mode='Markdown')
        
        bank_name = "Unknown Bank"
        country_name = "United States"
        country_code = "US"
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://lookup.binlist.net/{bin_num}", timeout=5.0)
                if resp.status_code == 200:
                    bin_data = resp.json()
                    bank_name = bin_data.get("bank", {}).get("name", "Unknown Bank").upper()
                    country_name = bin_data.get("country", {}).get("name", "United States")
                    country_code = bin_data.get("country", {}).get("alpha2", "US")
        except:
            pass 
            
        identity = generate_fake_identity(country_code)
        
        response_text = (
            f"✅ **SUCCESSFULLY GENERATED {q_text} CC!**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 `{cc_full_text}`\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 **Bank:** `{bank_name}`\n"
            f"🌍 **Country:** `{country_name}`\n"
            f"👤 **Name:** `{identity['name']}`\n"
            f"🌐 **IP Address:** `{identity['ip']}`\n"
            f"📞 **Phone Details:** `{identity['phone']}`\n"
            f"📮 **Zipcode:** `{identity['zipcode']}`\n"
            f"📍 **Street Address:** `{identity['street']}`\n"
            f"🏙 **State:** `{identity['state']}`\n"
            f"🌍 **Country:** `{country_name}`\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ *Check now! If invalid, click Not Working.*"
        )
        keyboard = [[InlineKeyboardButton("✅ Working", callback_data='fb_working'), InlineKeyboardButton("❌ Not Working", callback_data=f'fb_not_working_{COST}')]]
        await query.message.edit_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await query.answer(f"⚠️ {q_text} Stock Empty!", show_alert=True)
    conn.close()

# 5. FEEDBACK
async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == 'fb_working':
        await query.answer("❤️ Awesome!")
        context.user_data['waiting_for_proof'] = 'hit_proof'
        await query.message.edit_text("✅ **WORKING!**\n🔥 Please send a screenshot of your hit/success now.", parse_mode='Markdown')
    elif data.startswith('fb_not_working_'):
        cost = data.split('_')[-1]
        await query.answer()
        context.user_data['waiting_for_proof'] = f'report_{cost}'
        await query.message.edit_text("❌ **REPORT MODE**\nPlease send a screenshot of the error now.", parse_mode='Markdown')

# 6. DEPOSIT INFO & METHOD SELECTION
async def deposit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💸 **DEPOSIT & PRICING LIST**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 **Starter Plan:** 50 BDT / $0.50 ➔ 200 Credits\n"
        "🔵 **Basic Plan:** 100 BDT / $1.00 ➔ 500 Credits\n"
        "🟣 **Pro Plan:** 300 BDT / $3.00 ➔ 2500 Credits\n"
        "⚡ **Max Plan:** 1000 BDT / $10.00 ➔ 10,000 Credits\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 **SELECT PAYMENT METHOD:**"
    )
    kb = [
        [InlineKeyboardButton("🟣 Bkash", callback_data='method_bkash'), InlineKeyboardButton("🟠 Nagad", callback_data='method_nagad')],
        [InlineKeyboardButton("🟡 Binance Pay", callback_data='method_binance')],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')]
    ]
    if update.callback_query: 
        await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def payment_method_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    method = query.data.split('_')[1] 
    
    context.user_data['deposit_method'] = method
    context.user_data['waiting_for_proof'] = 'deposit_ss'

    if method == 'bkash':
        details = f"📱 **Bkash Personal:** `{BKASH_NUMBER}`"
    elif method == 'nagad':
        details = f"📱 **Nagad Personal:** `{NAGAD_NUMBER}`"
    else:
        details = f"🟡 **Binance Pay ID:** `{BINANCE_PAY_ID}`"

    text = (
        f"💳 **PAY VIA {method.upper()}**\n\n"
        f"{details}\n\n"
        "⚠️ **STEP 1:** Send the money to the details above.\n"
        "⚠️ **STEP 2:** Send the payment **Screenshot** here."
    )
    kb = [[InlineKeyboardButton("🔙 Back to Deposit", callback_data='deposit_info')]]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

# 7. SCREENSHOT LOGS 
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo = update.message.photo[-1].file_id
    state = context.user_data.get('waiting_for_proof')
    user_link = f"[{user.first_name}](tg://user?id={user.id})"
    
    if state == 'deposit_ss':
        context.user_data['deposit_photo'] = photo
        context.user_data['waiting_for_proof'] = 'deposit_trxid'
        await update.message.reply_text(
            "✅ **Screenshot Received!**\n\n"
            "📝 Now, please type and send the **Transaction ID (TrxID)** or Binance Order ID."
        )
        
    elif state and state.startswith('report_'):
        cost = state.split('_')[1]
        caption = f"🚨 **REPORT**\n👤 From: {user_link}\n⚠️ Issue: CC Not Working."
        keyboard = [[InlineKeyboardButton(f"♻️ Refund {cost} Cr", callback_data=f"refund_{user.id}_{cost}")], [InlineKeyboardButton("❌ Reject", callback_data="reject_action")]]
        await update.message.reply_text("✅ Report Sent to Admin.")
        context.user_data['waiting_for_proof'] = None
        try: 
            await context.bot.send_photo(chat_id=ADMIN_LOG_ID, photo=photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e: 
            pass
            
    elif state == 'hit_proof':
        caption = f"🔥 **SUCCESSFUL HIT!**\n👤 By: {user_link}\n✅ CC is working perfectly!"
        await update.message.reply_text("❤️ Thanks for sharing your hit!")
        context.user_data['waiting_for_proof'] = None
        try: 
            await context.bot.send_photo(chat_id=PUBLIC_LOG_ID, photo=photo, caption=caption, parse_mode='Markdown')
        except Exception as e: 
            pass 
            
    else:
        await update.message.reply_text("⚠️ Please go to the Deposit menu and select a payment method first.")

# 8. TEXT HANDLER FOR TRXID
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('waiting_for_proof')
    if state == 'deposit_trxid':
        trxid = update.message.text
        photo = context.user_data.get('deposit_photo')
        method = context.user_data.get('deposit_method', 'Unknown').upper()
        user = update.effective_user
        user_link = f"[{user.first_name}](tg://user?id={user.id})"

        caption = (
            f"💰 **NEW DEPOSIT REQUEST**\n"
            f"👤 From: {user_link} (`{user.id}`)\n"
            f"💳 Method: `{method}`\n"
            f"🧾 **TrxID:** `{trxid}`\n\n"
            f"ℹ️ Verify TrxID & Approve:"
        )
        keyboard = [
            [InlineKeyboardButton("Starter (200 Cr)", callback_data=f"pay_{user.id}_200_Starter")],
            [InlineKeyboardButton("Basic (500 Cr)", callback_data=f"pay_{user.id}_500_Basic")],
            [InlineKeyboardButton("Pro (2500 Cr)", callback_data=f"pay_{user.id}_2500_Pro")],
            [InlineKeyboardButton("Ultra (4500 Cr)", callback_data=f"pay_{user.id}_4500_Ultra")],
            [InlineKeyboardButton("Max (10000 Cr)", callback_data=f"pay_{user.id}_10000_Max")],
            [InlineKeyboardButton("❌ Reject", callback_data="reject_action")]
        ]
        
        await update.message.reply_text("✅ **Deposit Request Sent!**\nPlease wait for admin approval.")
        
        try: 
            await context.bot.send_photo(chat_id=ADMIN_LOG_ID, photo=photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e: 
            pass

        context.user_data['waiting_for_proof'] = None
        context.user_data['deposit_photo'] = None
        context.user_data['deposit_method'] = None

# 9. ADMIN ACTIONS
async def admin_log_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id): return
    data = query.data
    conn = get_db_connection()
    c = conn.cursor()

    if data.startswith("refund_"):
        parts = data.split("_")
        target_id = int(parts[1])
        refund_amount = int(parts[2])
        
        c.execute("UPDATE users SET credits = credits + %s WHERE user_id=%s", (refund_amount, target_id))
        conn.commit()
        await query.answer("✅ Refunded!")
        await query.message.edit_caption(caption=query.message.caption + f"\n\n✅ **REFUNDED ({refund_amount} Cr)**")
        try: await context.bot.send_message(target_id, f"✅ {refund_amount} Credits Refunded!")
        except: pass

    elif data.startswith("pay_"):
        parts = data.split("_")
        target_id, amount, plan = int(parts[1]), int(parts[2]), parts[3]
        c.execute("UPDATE users SET credits = credits + %s, role = %s WHERE user_id=%s", (amount, plan, target_id))
        conn.commit()
        await query.answer(f"✅ Approved {plan}!")
        await query.message.edit_caption(caption=query.message.caption + f"\n\n✅ **APPROVED: {plan}**")
        try: await context.bot.send_message(target_id, f"✅ **Payment Received!**\nPackage: {plan}\nCredits: +{amount}")
        except: pass
        try: await context.bot.send_message(PUBLIC_LOG_ID, f"⚡ **PREMIUM PURCHASED!**\n👤 User: `{target_id}`\n💎 Plan: `{plan}`", parse_mode='Markdown')
        except: pass

    elif data == "reject_action":
        await query.message.delete()
        
    conn.close()

# 10. ADMIN COMMANDS
async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return 
    try:
        new_admin = int(context.args[0])
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO admins (admin_id) VALUES (%s) ON CONFLICT (admin_id) DO NOTHING", (new_admin,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ User `{new_admin}` is now an Admin!", parse_mode='Markdown')
    except:
        await update.message.reply_text("⚠️ Usage: `/admin <user_id>`")

async def add_cc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: `/addcc normal 4108...` OR `/addcc hq 4108...`")
        return
    
    q_type = context.args[0].lower()
    if q_type not in ['normal', 'hq']:
        await update.message.reply_text("⚠️ Type must be 'normal' or 'hq'.")
        return
        
    cc_data = " ".join(context.args[1:])
    table = 'ccs_normal' if q_type == 'normal' else 'ccs_hq'
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"INSERT INTO {table} (cc_info) VALUES (%s)", (cc_data,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ CC Successfully Added to {q_type.upper()} Stock:\n💳 `{cc_data}`", parse_mode='Markdown')

async def delete_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args or context.args[0].lower() not in ['normal', 'hq']:
        await update.message.reply_text("⚠️ Usage: `/delete normal` OR `/delete hq`")
        return
        
    q_type = context.args[0].lower()
    table = 'ccs_normal' if q_type == 'normal' else 'ccs_hq'
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"DELETE FROM {table}") 
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"🗑️ **{q_type.upper()} STOCK CLEARED!**", parse_mode='Markdown')

async def active_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT full_name, user_id, credits, generated_count FROM users ORDER BY generated_count DESC LIMIT 10")
    users = c.fetchall()
    conn.close()
    if not users:
        await update.message.reply_text("❌ No active users.")
        return
    msg = f"📊 **TOP ACTIVE USERS**\n━━━━━━━━━━━━━━━━━━\n"
    for i, u in enumerate(users, 1):
        name = u[0] if u[0] else "User"
        mention = f"[{name}](tg://user?id={u[1]})"
        msg += f"{i}. {mention} | 💰 {u[2]} | 📦 **{u[3]}**\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_get_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args or context.args[0].lower() not in ['normal', 'hq']:
        await update.message.reply_text("⚠️ Usage: `/adminget normal` OR `/adminget hq`")
        return
        
    q_type = context.args[0].lower()
    table = 'ccs_normal' if q_type == 'normal' else 'ccs_hq'
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"SELECT id, cc_info FROM {table} ORDER BY RANDOM() LIMIT 1")
    acc = c.fetchone()
    if acc:
        c.execute(f"DELETE FROM {table} WHERE id=%s", (acc[0],)) 
        conn.commit()
        await update.message.reply_text(f"👑 **ADMIN GET ({q_type.upper()})**\n💳 `{acc[1]}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ {q_type.upper()} Stock Empty!")
    conn.close()

# 11. FILE UPLOAD & OTHER COMMANDS
async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    file = await update.message.document.get_file()
    file_path = f"stock_{update.effective_user.id}.txt"
    await file.download_to_drive(file_path)
    
    kb = [
        [InlineKeyboardButton("🔵 Normal Stock", callback_data='addstock_normal')],
        [InlineKeyboardButton("🟣 HQ Stock", callback_data='addstock_hq')]
    ]
    await update.message.reply_text("📁 File received! Which stock do you want to add these to?", reply_markup=InlineKeyboardMarkup(kb))

async def process_stock_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    table = 'ccs_normal' if q.data == 'addstock_normal' else 'ccs_hq'
    file_path = f"stock_{q.from_user.id}.txt"
    
    if not os.path.exists(file_path):
        await q.answer("❌ File not found! Please upload again.", show_alert=True)
        return
        
    await q.message.edit_text(f"⏳ Scanning and adding CCs to {table.upper()}...")
    try:
        conn = get_db_connection()
        c = conn.cursor()
        count = 0
        pattern = re.compile(r'(\d{15,16}[|]\d{1,2}[|]\d{2,4}[|]\d{3,4})')
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for cc in pattern.findall(f.read()):
                c.execute(f"INSERT INTO {table} (cc_info) VALUES (%s)", (cc,))
                count += 1
                
        conn.commit(); conn.close(); os.remove(file_path)
        await q.message.edit_text(f"✅ Successfully added {count} CCs to {table.upper()}.")
    except Exception as e: 
        await q.message.edit_text(f"❌ Error: {e}")

async def gen_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        amt = int(context.args[0])
        role = context.args[1].upper() if len(context.args) > 1 else "PREMIUM"
        code = generate_minato_code(role)
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO codes (code, credit_amount, role_reward, is_redeemed) VALUES (%s,%s,%s,0)", (code, amt, role))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"`{code}`")
    except: pass

async def add_credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        tid, amt = int(context.args[0]), int(context.args[1])
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET credits=credits+%s WHERE user_id=%s", (amt, tid))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ Done")
    except: pass

async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        code = context.args[0].strip(); uid = update.effective_user.id
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM codes WHERE code=%s AND is_redeemed=0", (code,))
        res = c.fetchone()
        if res:
            c.execute("UPDATE codes SET is_redeemed=1 WHERE code=%s", (code,))
            c.execute("UPDATE users SET credits=credits+%s, role=%s WHERE user_id=%s", (res[1], res[2], uid))
            conn.commit()
            await update.message.reply_text(f"✅ Redeemed {res[1]} Cr!")
            try: await context.bot.send_message(PUBLIC_LOG_ID, f"⚡ **REDEEMED!**\n👤 User: `{uid}`\n💎 Role: `{res[2]}`", parse_mode='Markdown')
            except: pass
        else: await update.message.reply_text("❌ Invalid.")
        conn.close()
    except: await update.message.reply_text("Usage: `/redeem CODE`")

async def show_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    cmds = (
        "🛠 **ADMIN COMMANDS**\n"
        "1. `/addcc normal <card>` OR `/addcc hq <card>`\n"
        "2. `/admin <id>` - Add new Admin\n"
        "3. `/active` - Clickable User List\n"
        "4. `/adminget normal` OR `/adminget hq`\n"
        "5. `/delete normal` OR `/delete hq`\n"
        "6. `/gencode <amt> <role>`\n"
        "7. `/addcredit <id> <amt>`\n"
        "8. Upload `.txt` File -> Select Normal or HQ"
    )
    await update.message.reply_text(cmds)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛠 **USER COMMANDS & HELP**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🔹 `/start` - Open the main menu\n"
        "🔹 `/help` - Show this help message\n"
        "🔹 `/redeem <code>` - Redeem a credit code\n\n"
        "💡 **How to use:**\n"
        "1. Use /start to open the menu.\n"
        "2. Click 'Deposit / Buy' to check packages and pay.\n"
        "3. Click 'Open Store' to get cards.\n\n"
        f"👨‍💻 **Contact Admin:** [Ononto Hasan](tg://user?id={ADMIN_ID})\n"
        f"🌐 **Facebook:** [Official Profile]({FB_ID_LINK})"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# MAIN CALLBACK HANDLER
async def btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.data.startswith(('pay_', 'refund_', 'reject_')): await admin_log_actions(update, context)
    elif q.data == 'store_menu': await store_menu(update, context)
    elif q.data in ['gen_normal', 'gen_hq']: await generate_account(update, context)
    elif q.data in ['addstock_normal', 'addstock_hq']: await process_stock_file(update, context)
    elif q.data in ['profile', 'main_menu']: await start(update, context)
    elif q.data == 'deposit_info': await deposit_info(update, context)
    elif q.data == 'daily_bonus': await daily_bonus(update, context)
    elif q.data.startswith('method_'): await payment_method_handler(update, context)
    elif q.data == 'fb_working' or q.data.startswith('fb_not_working'): await feedback_handler(update, context)
    elif q.data == 'redeem_btn': await q.answer(); await q.message.reply_text("Type `/redeem CODE`")

def main():
    print("🤖 MINATO Bot Started with PostgreSQL...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command)) 
    app.add_handler(CommandHandler("cmds", show_cmds))
    app.add_handler(CommandHandler("active", active_users_command))
    app.add_handler(CommandHandler("adminget", admin_get_account))
    app.add_handler(CommandHandler("delete", delete_stock_command)) 
    app.add_handler(CommandHandler("gencode", gen_code_command))
    app.add_handler(CommandHandler("addcredit", add_credit_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("addcc", add_cc_command))
    app.add_handler(CommandHandler("admin", add_admin_command))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), upload_file))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(btn_handler))
    app.run_polling()

if __name__ == '__main__':
    main()
