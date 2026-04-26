import os
import requests
import telebot
import datetime
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID") 
API_KEY = os.getenv("API_KEY") 
CHANNEL_ID = "@Lulzsec_empire"
BASE_URL = "https://techvishalboss.com/api/v1/lookup.php"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is Online and Stable!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- UTILS ---

def get_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12: return "Good Morning"
    elif 12 <= hour < 17: return "Good Afternoon"
    elif 17 <= hour < 21: return "Good Evening"
    else: return "Good Night"

def is_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

def clean_and_format(data, title):
    """Markdown parsing errors se bachne ke liye text ko saaf karta hai"""
    if not data or not data.get("success"):
        return "❌ **No details found for this input.**"

    priority = ['name', 'father_name', 'address', 'mobile', 'owner_name', 'number', 'rc_no']
    blocked = ['branding', 'owner', 'credit', 'status', 'success', 'key_status']

    res = f"📑 **{title.upper()}**\n"
    res += "━━━━━━━━━━━━━━━━━━━━\n"

    # Pehle priority wali info (Saaf format mein)
    for key in priority:
        if key in data and data[key]:
            val = str(data[key]).replace('_', ' ').replace('*', '') # Character Clean
            res += f"👤 **{key.replace('_',' ').title()}**: `{val}`\n"

    # Baaki info
    for k, v in data.items():
        if k not in priority and k not in blocked and v:
            val = str(v).replace('_', ' ').replace('*', '')
            res += f"🔹 **{k.replace('_',' ').title()}**: `{val}`\n"

    res += "━━━━━━━━━━━━━━━━━━━━\n"
    res += "✅ **Data Fetched Successfully**"
    return res

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    greet = get_greeting()

    # Admin Logging
    log = (f"👤 **New User Notification**\n"
           f"Name: {user.first_name}\n"
           f"ID: `{user.id}`\n"
           f"User: @{user.username if user.username else 'N/A'}")
    if OWNER_ID:
        try: bot.send_message(OWNER_ID, log, parse_mode="Markdown")
        except: pass

    welcome_text = (f"✨ {greet}, **{user.first_name}**!\n\n"
                    f"Sir, ensure that you joined the **{CHANNEL_ID}** to continue.\n\n"
                    f"⚠️ *Note:* This bot only works in **Groups** for security.\n\n"
                    f"**Commands:**\n"
                    f"🔹 `/no [number]` - Phone Lookup\n"
                    f"🔹 `/tg [id/user]` - TG Lookup\n"
                    f"🔹 `/vec [RC]` - Vehicle Details\n"
                    f"🔹 `/id` - Get your/other's ID")
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def get_id(message):
    # Case 1: Reply karke /id bolna
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        bot.reply_to(message, f"👤 **User:** {target.first_name}\n🆔 **ID:** `{target.id}`", parse_mode="Markdown")
    # Case 2: Mention karke /id @user (Sirf tab kaam karega agar bot ne use pehle dekha ho)
    elif len(message.text.split()) > 1:
        # Note: Username se ID nikalne ke liye bot ka database ya full access chahiye hota hai
        bot.reply_to(message, "ℹ️ Use `/id` by replying to a user's message.")
    # Case 3: Khud ki ID
    else:
        bot.reply_to(message, f"🆔 Your ID: `{message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['no', 'tg', 'vec'])
def main_handler(message):
    user_id = message.from_user.id

    # 1. Force Join
    if not is_joined(user_id):
        bot.reply_to(message, f"❌ **Join Required**\n\nSir, please join {CHANNEL_ID} first!")
        return

    # 2. Group Check
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ **Security Alert**\n\nSir, results are only shown in groups.")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❗ **Input Missing!**\nUsage: `/[cmd] [value]`")
        return

    cmd, val = args[0].lower(), args[1]
    wait = bot.reply_to(message, "⚡ **Scanning Databases...**")

    try:
        if cmd == "/no":
            data = requests.get(BASE_URL, params={"key": API_KEY, "service": "number", "number": val}, timeout=15).json()
            msg = clean_and_format(data, "Number Identity")

        elif cmd == "/tg":
            data = requests.get(BASE_URL, params={"key": API_KEY, "service": "tg_to_number", "telegram": val}, timeout=15).json()
            msg = clean_and_format(data, "Telegram Data")
            
        elif cmd == "/vec":
            v_info = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle", "rc": val}, timeout=15).json()
            v_owner = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle_owner_number", "rc": val}, timeout=15).json()
            if v_info.get("success"):
                v_info.update(v_owner) 
                msg = clean_and_format(v_info, "Vehicle Ownership")
            else:
                msg = "❌ Vehicle not found."

        bot.edit_message_text(msg, message.chat.id, wait.message_id, parse_mode="Markdown")

    except Exception:
        bot.edit_message_text("❌ **API Timeout or Invalid Input.**", message.chat.id, wait.message_id)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
