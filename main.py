import os
import requests
import telebot
import datetime
from flask import Flask
from threading import Thread
from telebot import types # Buttons functionality
from dotenv import load_dotenv

# Load local .env file if it exists
load_dotenv()

# --- CONFIGURATION ---
# These are pulled from Render's Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY") 
CHANNEL_ID = "@Lulzsec_empire" 
CHANNEL_LINK = "https://t.me/Lulzsec_empire"
BASE_URL = "https://techvishalboss.com/api/v1/lookup.php"

# Convert OWNER_ID to integer safely to avoid bot.send_message errors
OWNER_ID_RAW = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW and OWNER_ID_RAW.isdigit() else None

# Initialize Bot
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not found! Make sure it's set in Environment Variables.")
else:
    bot = telebot.TeleBot(BOT_TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot is Online and Health Check Passed!"

def run_flask():
    # Render uses the 'PORT' environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

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
    except Exception:
        return False

def escape_md(text):
    if not text: return "N/A"
    return str(text).replace('_', ' ').replace('*', '').replace('`', '')

# --- START HANDLER ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    greet = get_greeting()

    markup = types.InlineKeyboardMarkup()
    btn_join = types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)
    markup.add(btn_join)

    welcome_text = (f"✨ {greet}, **{user.first_name}**!\n\n"
                    f"Sir, please ensure you have joined our channel to use this bot.\n\n"
                    f"⚠️ **Note:** This bot works only in Groups for security.\n\n"
                    f"**Available Commands:**\n"
                    f"🔹 `/no [number]` - Number Lookup\n"
                    f"🔹 `/tg [id/user]` - Telegram Lookup\n"
                    f"🔹 `/vec [RC]` - Vehicle Details\n"
                    f"🔹 `/id` - Check User ID")

    # Admin Alert (OWNER_ID must be an integer)
    if OWNER_ID:
        try:
            bot.send_message(OWNER_ID, f"👤 **New User:** {user.first_name}\n🆔 `{user.id}`", parse_mode="Markdown")
        except Exception:
            pass

    try:
        photos = bot.get_user_profile_photos(user.id)
        if photos and photos.total_count > 0:
            bot.send_photo(message.chat.id, photos.photos[0][-1].file_id, caption=welcome_text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- OTHER COMMANDS ---

@bot.message_handler(commands=['id'])
def handle_id(message):
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        bot.reply_to(message, f"👤 **Name:** {target.first_name}\n🆔 **ID:** `{target.id}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"🆔 **Your ID:** `{message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['no', 'tg', 'vec'])
def main_handler(message):
    user_id = message.from_user.id

    # Join Check
    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Now", url=CHANNEL_LINK))
        bot.reply_to(message, "❌ **Access Denied!**\n\nSir, join the channel first to continue.", reply_markup=markup)
        return

    # Group Check
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ **Group Only!**\n\nSir, this bot works only in groups for security reasons.")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, f"❗ **Input missing!**\nExample: `{args[0]} [value]`")
        return

    cmd, val = args[0].lower(), args[1]
    wait = bot.reply_to(message, "⚡ **Fetching Data...**")

    try:
        data = None
        title = ""

        if cmd == "/no":
            response = requests.get(BASE_URL, params={"key": API_KEY, "service": "number", "number": val}, timeout=15)
            data = response.json()
            title = "Number Details"
        elif cmd == "/tg":
            response = requests.get(BASE_URL, params={"key": API_KEY, "service": "tg_to_number", "telegram": val}, timeout=15)
            data = response.json()
            title = "Telegram Identity"
        elif cmd == "/vec":
            v_info_res = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle", "rc": val}, timeout=15)
            v_owner_res = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle_owner_number", "rc": val}, timeout=15)
            v_info = v_info_res.json()
            v_owner = v_owner_res.json()
            
            if v_info.get("success"):
                v_info.update(v_owner)
                data, title = v_info, "Vehicle & Owner"
            else:
                data = v_info

        if not data or not data.get("success"):
            bot.edit_message_text("❌ No data found or API Error.", message.chat.id, wait.message_id)
            return

        # Formatting Output
        res_msg = f"📑 **{title.upper()}**\n━━━━━━━━━━━━━━\n"
        priority = ['name', 'father_name', 'address', 'mobile', 'owner_name', 'number']
        
        # Add priority fields first
        for k in priority:
            if k in data and data[k]:
                res_msg += f"👤 **{k.replace('_',' ').title()}**: `{escape_md(data[k])}`\n"

        # Add all other fields
        for k, v in data.items():
            if k not in priority and k not in ['success', 'branding', 'status', 'credit'] and v:
                res_msg += f"🔹 **{k.replace('_',' ').title()}**: `{escape_md(v)}`\n"

        res_msg += "━━━━━━━━━━━━━━\n✅ Verified"
        bot.edit_message_text(res_msg, message.chat.id, wait.message_id, parse_mode="Markdown")

    except Exception as e:
        print(f"Error: {e}")
        bot.edit_message_text("❌ Error processing request or Connection Timeout.", message.chat.id, wait.message_id)

if __name__ == "__main__":
    try:
        # Start Flask thread
        print("Starting Flask server...")
        Thread(target=run_flask, daemon=True).start()
        
        # Start Bot
        print("Bot is attempting to poll...")
        if not BOT_TOKEN:
            print("CRITICAL ERROR: BOT_TOKEN is missing!")
        else:
            bot.infinity_polling(skip_pending=True)
            
    except Exception as e:
        print(f"CRITICAL CRASH: {e}")
