import os
import requests
import telebot
import datetime
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Environment variables load karein
load_dotenv()

# --- CONFIGURATION ---
# Render ke Environment Variables mein ye sab set karein
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

# --- UTILS (Cleaning & Greetings) ---

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

def clean_text(text):
    """Markdown crash rokne ke liye characters clean karta hai"""
    if not text: return "N/A"
    return str(text).replace('_', ' ').replace('*', '').replace('`', '')

def format_output(data, title):
    """Results ko Name, Father Name, Address format mein dikhane ke liye"""
    if not data or not data.get("success"):
        return "❌ **No details found in database.**"

    # Inko sequence mein dikhayenge
    priority = ['name', 'father_name', 'address', 'mobile', 'owner_name', 'number', 'rc_no']
    blocked = ['branding', 'owner', 'credit', 'status', 'success', 'key_status']

    msg = f"📑 **{title.upper()}**\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"

    # Pehle main info
    for key in priority:
        if key in data and data[key]:
            val = clean_text(data[key])
            msg += f"👤 **{key.replace('_',' ').title()}**: `{val}`\n"

    # Phir baaki bachi details
    for k, v in data.items():
        if k not in priority and k not in blocked and v:
            val = clean_text(v)
            msg += f"🔹 **{k.replace('_',' ').title()}**: `{val}`\n"

    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "✅ **Data Fetched Successfully**"
    return msg

# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    greet = get_greeting()

    # Admin Alert
    log = (f"👤 **New User Alert**\n"
           f"Name: {user.first_name}\n"
           f"ID: `{user.id}`\n"
           f"User: @{user.username if user.username else 'None'}")
    if OWNER_ID:
        try: bot.send_message(OWNER_ID, log, parse_mode="Markdown")
        except: pass

    welcome_text = (f"✨ {greet}, **{user.first_name}**!\n\n"
                    f"Sir, ensure that you joined the **{CHANNEL_ID}** to continue.\n\n"
                    f"⚠️ *Note:* For security reasons, this bot only works in groups.\n\n"
                    f"**Commands:**\n"
                    f"🔹 `/no [number]` - Phone Lookup\n"
                    f"🔹 `/tg [id/user]` - Telegram Lookup\n"
                    f"🔹 `/vec [RC]` - Vehicle Details\n"
                    f"🔹 `/id` - Get ID (Reply/Self)")

    try:
        # DP ke saath welcome
        photos = bot.get_user_profile_photos(user.id)
        if photos.total_count > 0:
            bot.send_photo(message.chat.id, photos.photos[0][-1].file_id, caption=welcome_text, parse_mode="Markdown")
        else:
            bot.reply_to(message, welcome_text, parse_mode="Markdown")
    except:
        bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def handle_id(message):
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        bot.reply_to(message, f"👤 **User:** {target.first_name}\n🆔 **ID:** `{target.id}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"🆔 Your ID: `{message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['no', 'tg', 'vec'])
def main_handler(message):
    user_id = message.from_user.id

    # 1. Force Join Check
    if not is_joined(user_id):
        bot.reply_to(message, f"❌ **Access Denied!**\n\nSir, please join {CHANNEL_ID} to use me.")
        return

    # 2. Group Check
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ **Security Alert!**\n\nSir, this bot only works in Groups.")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❗ **Input missing!**\nExample: `/no 91888...` or `/vec UP32...`", parse_mode="Markdown")
        return

    cmd, val = args[0].lower(), args[1]
    wait = bot.reply_to(message, "⚡ **Searching Databases...**")

    try:
        if cmd == "/no":
            data = requests.get(BASE_URL, params={"key": API_KEY, "service": "number", "number": val}, timeout=15).json()
            msg = format_output(data, "Number Details")

        elif cmd == "/tg":
            data = requests.get(BASE_URL, params={"key": API_KEY, "service": "tg_to_number", "telegram": val}, timeout=15).json()
            msg = format_output(data, "Telegram Identity")

        elif cmd == "/vec":
            # Vehicle Info + Owner Mobile Number (Double API)
            v_info = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle", "rc": val}, timeout=15).json()
            v_owner = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle_owner_number", "rc": val}, timeout=15).json()
            
            if v_info.get("success"):
                v_info.update(v_owner) # Merging owner data into info
                msg = format_output(v_info, "Vehicle & Owner Details")
            else:
                msg = "❌ Vehicle not found."

        bot.edit_message_text(msg, message.chat.id, wait.message_id, parse_mode="Markdown")

    except Exception:
        bot.edit_message_text("❌ **Server Error or Invalid Request.**", message.chat.id, wait.message_id)

# --- EXECUTION ---

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print("Bot is starting...")
    bot.infinity_polling(skip_pending=True)
