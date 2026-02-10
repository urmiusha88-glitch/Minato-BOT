import logging
import sqlite3
import random
import string
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

# ======================================================
# 👇 CONFIGURATION SECTION (MUST EDIT THIS)
# ======================================================
TOKEN = "8290942305:AAGHVDfo3PlvK3atxn9CGIGqndbd5RTQFqk"  # Bot Token
ADMIN_ID = 6198703244  # Your Telegram ID
PAYMENT_NUMBER = "01846849460"  # Bkash/Nagad Number

# 🔴 GROUP & CHANNEL IDS (Must start with -100)
ADMIN_LOG_ID = -1003769033152
PUBLIC_LOG_ID = -1003775622081
CHANNEL_ID = -5117274883

# 🔗 INVITE LINK
CHANNEL_INVITE_LINK = "https://t.me/+cBcd9vR84Bc2OWU1"
# ======================================================
FB_ID_LINK ="https://www.facebook.com/yours.ononto"
FB_PAGE_LINK = "https://www.facebook.com/toxicnaaa69"
# ======================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('minato_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, credits INTEGER, role TEXT, generated_count INTEGER DEFAULT 0, full_name TEXT)''')
    # Accounts table - 'is_used' removed as we delete rows now
    c.execute('''CREATE TABLE IF NOT EXISTS accounts 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS codes 
                 (code TEXT PRIMARY KEY, credit_amount INTEGER, role_reward TEXT, is_redeemed INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- HELPER ---
def get_user(user_id, first_name="Unknown"):
    conn = sqlite3.connect('minato_bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, credits, role, generated_count, full_name) VALUES (?, ?, ?, 0, ?)", (user_id, 0, 'Free', first_name))
        conn.commit()
        user = (user_id, 0, 'Free', 0, first_name)
    else:
        if first_name != "Unknown":
            c.execute("UPDATE users SET full_name=? WHERE user_id=?", (first_name, user_id))
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
    except: return True 

# --- HANDLERS ---

# 1. START MENU
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await check_join(user.id, context):
        await update.message.reply_text(
            f"❌ **ACCESS DENIED**\n\n⚠️ You must join our channel first.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_INVITE_LINK)]])
        )
        return

    db_user = get_user(user.id, user.first_name)
    
    welcome_text = (
        f"🌟 **WELCOME TO MINATO SERVICES** 🌟\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 **Hi, {user.first_name}**\n\n"
        f"💎 **Credits:** `{db_user[1]}`\n"
        f"👑 **Status:** `{db_user[2]}`\n"
        f"📦 **Generated:** `{db_user[3]}`\n"
        f"🆔 **Account ID:** `{user.id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ _Premium Accounts at Cheapest Rate!_\n\n"
        f"👨‍💻 **Developer:** [Ononto Hasan]({FB_ID_LINK})\n"
        f"📢 **Page:** [Official Page]({FB_PAGE_LINK})"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎁 Generate Account", callback_data='gen_acc')],
        [InlineKeyboardButton("💸 Deposit / Buy", callback_data='deposit_info')],
        [InlineKeyboardButton("👤 My Profile", callback_data='profile'), InlineKeyboardButton("💎 Redeem Code", callback_data='redeem_btn')],
        [InlineKeyboardButton("📞 Contact Admin", url=FB_ID_LINK)] 
    ]
    
    if update.message: await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else: 
        try: await update.callback_query.message.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except: pass

# 2. GENERATE ACCOUNT (AUTO DELETE FEATURE)
async def generate_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not await check_join(user_id, context):
        await query.answer("❌ Join Channel First!", show_alert=True)
        return

    db_user = get_user(user_id)
    COST = 100
    
    if db_user[1] < COST:
        await query.answer(f"❌ Low Balance! Need {COST} Credits.", show_alert=True)
        return

    conn = sqlite3.connect('minato_bot.db')
    c = conn.cursor()
    
    # Select ANY account (Since we delete them, all remaining are unused)
    c.execute("SELECT id, email, password FROM accounts ORDER BY RANDOM() LIMIT 1")
    account = c.fetchone()
    
    if account:
        # 1. Deduct Credits & Increase Count
        c.execute("UPDATE users SET credits = credits - ?, generated_count = generated_count + 1 WHERE user_id=?", (COST, user_id))
        
        # 2. 🔥 AUTO DELETE: Remove this account from DB permanently
        c.execute("DELETE FROM accounts WHERE id=?", (account[0],))
        conn.commit()
        
        response_text = (
            "✅ **SUCCESSFULLY GENERATED!**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 `{account[1]}`\n"
            f"🔑 `{account[2]}`\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ *Check now! If invalid, click Not Working.*"
        )
        keyboard = [[InlineKeyboardButton("✅ Working", callback_data='fb_working'), InlineKeyboardButton("❌ Not Working", callback_data='fb_not_working')]]
        await query.message.edit_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await query.answer("⚠️ Stock Empty!", show_alert=True)
    conn.close()

# 3. FEEDBACK
async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == 'fb_working':
        await query.answer("❤️ Thanks!")
        await query.message.edit_text("✅ **Enjoy your account!**", parse_mode='Markdown')
    elif data == 'fb_not_working':
        await query.answer()
        context.user_data['waiting_for_proof'] = 'report'
        await query.message.edit_text("❌ **REPORT MODE**\nPlease send a screenshot of the error now.", parse_mode='Markdown')

# 4. SCREENSHOT LOGS
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo = update.message.photo[-1].file_id
    state = context.user_data.get('waiting_for_proof')
    user_link = f"[{user.first_name}](tg://user?id={user.id})"
    
    caption = ""
    keyboard = []
    
    if state == 'report':
        caption = f"🚨 **REPORT**\n👤 From: {user_link}\n⚠️ Issue: Account Not Working."
        keyboard = [[InlineKeyboardButton(f"♻️ Refund 100 Cr", callback_data=f"refund_{user.id}")], [InlineKeyboardButton("❌ Reject", callback_data="reject_action")]]
        await update.message.reply_text("✅ Report Sent.")
        context.user_data['waiting_for_proof'] = None
    else:
        caption = f"💰 **DEPOSIT**\n👤 From: {user_link}\nℹ️ Verify TrxID & Approve:"
        keyboard = [
            [InlineKeyboardButton("Starter (200 Cr)", callback_data=f"pay_{user.id}_200_Starter")],
            [InlineKeyboardButton("Basic (500 Cr)", callback_data=f"pay_{user.id}_500_Basic")],
            [InlineKeyboardButton("Pro (2500 Cr)", callback_data=f"pay_{user.id}_2500_Pro")],
            [InlineKeyboardButton("Ultra (4500 Cr)", callback_data=f"pay_{user.id}_4500_Ultra")],
            [InlineKeyboardButton("Max (10000 Cr)", callback_data=f"pay_{user.id}_10000_Max")],
            [InlineKeyboardButton("❌ Reject", callback_data="reject_action")]
        ]
        await update.message.reply_text("✅ Proof Received.")

    try: await context.bot.send_photo(chat_id=ADMIN_LOG_ID, photo=photo, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except Exception as e: await update.message.reply_text(f"⚠️ Log Error: {e}")

# 5. ADMIN ACTIONS
async def admin_log_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID: return
    data = query.data
    conn = sqlite3.connect('minato_bot.db')
    c = conn.cursor()

    if data.startswith("refund_"):
        target_id = int(data.split("_")[1])
        c.execute("UPDATE users SET credits = credits + 100 WHERE user_id=?", (target_id,))
        conn.commit()
        await query.answer("✅ Refunded!")
        await query.message.edit_caption(caption=query.message.caption + "\n\n✅ **REFUNDED**")
        try: await context.bot.send_message(target_id, "✅ 100 Credits Refunded!")
        except: pass

    elif data.startswith("pay_"):
        parts = data.split("_")
        target_id, amount, plan = int(parts[1]), int(parts[2]), parts[3]
        c.execute("UPDATE users SET credits = credits + ?, role = ? WHERE user_id=?", (amount, plan, target_id))
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

# 6. ADMIN COMMANDS

# 🔥 DELETE STOCK COMMAND
async def delete_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    conn = sqlite3.connect('minato_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM accounts") # Deletes EVERYTHING from accounts table
    conn.commit()
    conn.close()
    
    await update.message.reply_text("🗑️ **STOCK CLEARED!**\nAll accounts have been deleted from the database.", parse_mode='Markdown')

async def active_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    conn = sqlite3.connect('minato_bot.db')
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
    if update.effective_user.id != ADMIN_ID: return
    conn = sqlite3.connect('minato_bot.db')
    c = conn.cursor()
    c.execute("SELECT id, email, password FROM accounts ORDER BY RANDOM() LIMIT 1")
    acc = c.fetchone()
    if acc:
        c.execute("DELETE FROM accounts WHERE id=?", (acc[0],)) # Admin nileo delete hoye jabe
        conn.commit()
        await update.message.reply_text(f"👑 **ADMIN GET**\n📧 `{acc[1]}`\n🔑 `{acc[2]}`", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Stock Empty!")
    conn.close()

# 7. OTHER COMMANDS
async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = await update.message.reply_text("⏳ Scanning...")
    try:
        file = await update.message.document.get_file()
        await file.download_to_drive("stock.txt")
        conn = sqlite3.connect('minato_bot.db')
        c = conn.cursor()
        count = 0
        pattern = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+):([^\s]+)')
        with open("stock.txt", 'r', encoding='utf-8', errors='ignore') as f:
            for email, password in pattern.findall(f.read()):
                c.execute("INSERT INTO accounts (email, password) VALUES (?, ?)", (email, password))
                count += 1
        conn.commit(); conn.close(); os.remove("stock.txt")
        await msg.edit_text(f"✅ Added {count} accounts.")
    except Exception as e: await msg.edit_text(f"❌ Error: {e}")

async def gen_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        amt = int(context.args[0])
        role = context.args[1].upper() if len(context.args) > 1 else "PREMIUM"
        code = generate_minato_code(role)
        sqlite3.connect('minato_bot.db').cursor().execute("INSERT INTO codes VALUES (?,?,?,0)", (code, amt, role)).connection.commit()
        await update.message.reply_text(f"`{code}`")
    except: pass

async def add_credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        tid, amt = int(context.args[0]), int(context.args[1])
        sqlite3.connect('minato_bot.db').cursor().execute("UPDATE users SET credits=credits+? WHERE user_id=?", (amt, tid)).connection.commit()
        await update.message.reply_text("✅ Done")
    except: pass

async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        code = context.args[0].strip(); uid = update.effective_user.id
        conn = sqlite3.connect('minato_bot.db'); c = conn.cursor()
        res = c.execute("SELECT * FROM codes WHERE code=? AND is_redeemed=0", (code,)).fetchone()
        if res:
            c.execute("UPDATE codes SET is_redeemed=1 WHERE code=?", (code,))
            c.execute("UPDATE users SET credits=credits+?, role=? WHERE user_id=?", (res[1], res[2], uid))
            conn.commit()
            await update.message.reply_text(f"✅ Redeemed {res[1]} Cr!")
            try: await context.bot.send_message(PUBLIC_LOG_ID, f"⚡ **REDEEMED!**\n👤 User: `{uid}`\n💎 Role: `{res[2]}`", parse_mode='Markdown')
            except: pass
        else: await update.message.reply_text("❌ Invalid.")
        conn.close()
    except: await update.message.reply_text("Usage: `/redeem CODE`")

async def show_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    cmds = (
        "🛠 **ADMIN COMMANDS**\n"
        "1. `/active` - Clickable User List\n"
        "2. `/adminget` - Free Account\n"
        "3. `/delete` - Clear ALL Stock (NEW)\n"
        "4. `/gencode <amt> <role>`\n"
        "5. `/addcredit <id> <amt>`\n"
        "6. Upload .txt File"
    )
    await update.message.reply_text(cmds)

async def deposit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💸 **DEPOSIT & PRICING LIST**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🟢 **Starter Plan**\n"
        "💰 Price: 50 BDT\n"
        "💎 Get: 200 Credits\n\n"
        "🔵 **Basic Plan**\n"
        "💰 Price: 100 BDT\n"
        "💎 Get: 500 Credits\n\n"
        "🟣 **Pro Plan**\n"
        "💰 Price: 300 BDT\n"
        "💎 Get: 2500 Credits\n\n"
        "⚡ **Max Plan**\n"
        "💰 Price: 1000 BDT\n"
        "💎 Get: 10,000 Credits\n\n"
        f"🚀 **Bkash / Nagad:** `{PAYMENT_NUMBER}`\n\n"
        "**👇 INSTRUCTIONS:**\n"
        "1. Send money.\n"
        "2. Send **Screenshot** here."
    )
    kb = [[InlineKeyboardButton("🔙 Back", callback_data='profile')]]
    if update.callback_query: await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

# MAIN
async def btn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.data.startswith(('pay_', 'refund_', 'reject_')): await admin_log_actions(update, context)
    elif q.data == 'gen_acc': await generate_account(update, context)
    elif q.data == 'profile': await start(update, context)
    elif q.data == 'deposit_info': await deposit_info(update, context)
    elif q.data in ['fb_working', 'fb_not_working']: await feedback_handler(update, context)
    elif q.data == 'redeem_btn': await q.answer(); await q.message.reply_text("Type `/redeem CODE`")

def main():
    print("🤖 MINATO Bot Started...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cmds", show_cmds))
    app.add_handler(CommandHandler("active", active_users_command))
    app.add_handler(CommandHandler("adminget", admin_get_account))
    app.add_handler(CommandHandler("delete", delete_stock_command)) # Notun Command
    app.add_handler(CommandHandler("gencode", gen_code_command))
    app.add_handler(CommandHandler("addcredit", add_credit_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), upload_file))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    app.add_handler(CallbackQueryHandler(btn_handler))
    app.run_polling()

if __name__ == '__main__':
    main()
