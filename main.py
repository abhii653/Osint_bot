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
OWNER_ID = os.getenv("OWNER_ID") # Aapki Telegram ID
API_KEY = os.getenv("API_KEY") 
CHANNEL_ID = "@Lulzsec_empire"
BASE_URL = "https://techvishalboss.com/api/v1/lookup.php"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is Online!"

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
    """Result ko properly line-by-line dikhane ke liye"""
    if not data or not data.get("success"):
        return "❌ **No details found for this input.**"
    
    # Priority keys jo upar dikhani hain
    priority = ['name', 'father_name', 'address', 'mobile', 'owner_name', 'number', 'rc_no']
    blocked = ['branding', 'owner', 'credit', 'status', 'success', 'key_status']
    
    res = f"📑 **{title.upper()}**\n"
    res += "━━━━━━━━━━━━━━━━━━━━\n"
    
    # Pehle priority wali info dikhao
    for key in priority:
        if key in data and data[key]:
            val = data[key]
            res += f"👤 **{key.replace('_',' ').title()}**: `{val}`\n"
    
    # Baaki bachi hui info
    for k, v in data.items():
        if k not in priority and k not in blocked and v:
            res += f"🔹 **{k.replace('_',' ').title()}**: `{v}`\n"
            
    res += "━━━━━━━━━━━━━━━━━━━━\n"
    res += "✅ **Verified Data**"
    return res

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user
    greet = get_greeting()
    
    # Admin Alert
    log = (f"👤 **New User Log**\n"
           f"Name: {user.first_name}\n"
           f"ID: `{user.id}`\n"
           f"User: @{user.username}")
    if OWNER_ID:
        try: bot.send_message(OWNER_ID, log, parse_mode="Markdown")
        except: pass

    welcome_text = (f"✨ {greet}, **{user.first_name}**!\n\n"
                    f"Sir, ensure that you joined the **{CHANNEL_ID}** to continue.\n\n"
                    f"⚠️ *Note:* For security reasons, this bot only works in groups.\n\n"
                    f"**Commands:**\n"
                    f"🔹 `/no [number]` - Phone Lookup\n"
                    f"🔹 `/tg [username/id]` - Telegram Lookup\n"
                    f"🔹 `/vec [RC]` - Vehicle Details\n"
                    f"🔹 `/id [reply/username]` - Get User ID")
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def get_id(message):
    # Agar kisi ke message pe reply karke /id likha
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        bot.reply_to(message, f"👤 **User:** {target.first_name}\n🆔 **ID:** `{target.id}`", parse_mode="Markdown")
    # Agar /id @username likha
    elif len(message.text.split()) > 1:
        bot.reply_to(message, "🔎 Looking up ID...")
        # Note: Bot ko user ki ID tabhi milegi agar bot us user ko pehle se jaanta ho
    else:
        bot.reply_to(message, f"🆔 Your ID: `{message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['no', 'tg', 'vec'])
def main_handler(message):
    user_id = message.from_user.id
    
    # 1. Force Join Check
    if not is_joined(user_id):
        bot.reply_to(message, f"❌ **Access Denied!**\n\nSir, please join our channel **{CHANNEL_ID}** to use this bot.")
        return

    # 2. Group Check
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ **Security Alert!**\n\nSir, this bot only works in Groups for privacy protection.")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❗ **Input missing!**\nExample: `/vec UP32XX0000`")
        return

    cmd = args[0].lower()
    val = args[1]
    wait = bot.reply_to(message, "⚡ **Processing Request...**")

    try:
        if cmd == "/no":
            data = requests.get(BASE_URL, params={"key": API_KEY, "service": "number", "number": val}).json()
            msg = clean_and_format(data, "Number Details")
        
        elif cmd == "/tg":
            data = requests.get(BASE_URL, params={"key": API_KEY, "service": "tg_to_number", "telegram": val}).json()
            msg = clean_and_format(data, "Telegram Lookup")
            
        elif cmd == "/vec":
            # Vehicle Info + Owner Details (Dono fetch karke merge karega)
            v_info = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle", "rc": val}).json()
            v_owner = requests.get(BASE_URL, params={"key": API_KEY, "service": "vehicle_owner_number", "rc": val}).json()
            
            # Merge logic
            if v_info.get("success"):
                v_info.update(v_owner) # Owner details ko basic info mein add kiya
                msg = clean_and_format(v_info, "Vehicle & Owner Details")
            else:
                msg = "❌ Vehicle data not found."

        bot.edit_message_text(msg, message.chat.id, wait.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.edit_message_text(f"❌ Error: Server issue or invalid input.", message.chat.id, wait.message_id)

if __name__ == "__main__":
    # Flask thread start karein
    Thread(target=run_flask, daemon=True).start()
    
    print("Bot is starting...")
    
    # skip_pending=True purane updates ko clear kar deta hai
    bot.infinity_polling(skip_pending=True)
