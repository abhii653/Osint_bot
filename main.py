import os
import requests
import telebot
import datetime
from flask import Flask
from threading import Thread
from telebot import types # Buttons ke liye
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID") 
API_KEY = os.getenv("API_KEY") 
CHANNEL_ID = "@Lulzsec_empire" # Bina '@' ke bhi try kar sakte hain agar error aaye
CHANNEL_LINK = "https://t.me/Lulzsec_empire"
BASE_URL = "https://techvishalboss.com/api/v1/lookup.php"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is Online!"

def run_flask():
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
    except: return False

def escape_md(text):
    if not text: return "N/A"
    return str(text).replace('_', ' ').replace('*', '').replace('`', '')

# --- START HANDLER (With Buttons & DP) ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    greet = get_greeting()
    
    # Inline Buttons banayein
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

    # Admin Alert
    if OWNER_ID:
        try: bot.send_message(OWNER_ID, f"👤 **New User:** {user.first_name}\n🆔 `{user.id}`", parse_mode="Markdown")
        except: pass

    try:
        photos = bot.get_user_profile_photos(user.id)
        if photos.total_count > 0:
            bot.send_photo(message.chat.id, photos.photos[0][-1].file_id, caption=welcome_text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
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

    if not is_joined(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Now", url=CHANNEL_LINK))
        bot.reply_to(message, "❌ **Access Denied!**\n\nSir, join the channel first to continue.", reply_markup=markup)
        return

    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ **Group Only!**\n\nSir, this bot works only in groups for security reasons.")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❗ **Input missing!**\nExample: `/vec UP32XX0000`")
        return

    cmd, val = args[0].lower(), args[1]
    wait = bot.reply_to(message, "⚡ **Fetching Data...**")

    try:
        if cmd == "/no":
            data = requests.get(BASE_URL, params={"key": API_KEY, "service": "number", "number": val}, timeout=15).json()
            title = "Number Details"
        elif cmd == "/tg":
            data = requests.get(BASE_URL, params={"key": API_KEY, "service": "tg_to_number", "telegram": val}, timeout=15).json()
            title = "Telegram Identity"
        elif cmd == "/vec":
            v_info = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle", "rc": val}, timeout=15).json()
            v_owner = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle_owner_number", "rc": val}, timeout=15).json()
            if v_info.get("success"):
                v_info.update(v_owner)
                data, title = v_info, "Vehicle & Owner"
            else: data = None

        if not data or not data.get("success"):
            bot.edit_message_text("❌ No data found.", message.chat.id, wait.message_id)
            return

        # Results formatting
        res_msg = f"📑 **{title.upper()}**\n━━━━━━━━━━━━━━\n"
        priority = ['name', 'father_name', 'address', 'mobile', 'owner_name', 'number']
        for k in priority:
            if k in data and data[k]:
                res_msg += f"👤 **{k.replace('_',' ').title()}**: `{escape_md(data[k])}`\n"
        
        for k, v in data.items():
            if k not in priority and k not in ['success', 'branding', 'status', 'credit'] and v:
                res_msg += f"🔹 **{k.replace('_',' ').title()}**: `{escape_md(v)}`\n"
        
        res_msg += "━━━━━━━━━━━━━━\n✅ Verified"
        bot.edit_message_text(res_msg, message.chat.id, wait.message_id, parse_mode="Markdown")

    except Exception:
        bot.edit_message_text("❌ Error processing request.", message.chat.id, wait.message_id)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    print("Bot is Starting...")
    bot.infinity_polling(skip_pending=True)
