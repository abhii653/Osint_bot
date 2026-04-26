import os
import requests
import telebot
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Environment variables load karein
load_dotenv()

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
API_KEY = os.getenv("API_KEY") 
CHANNEL_ID = "@Lulzsec_empire"
BASE_URL = "https://techvishalboss.com/api/v1/lookup.php"

# Bot initialization
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# --- WEB SERVER FOR RENDER (Keep-Alive & Port Binding) ---
@app.route('/')
def home():
    return "Bot is Alive and Running!"

def run_flask():
    # Render automatically PORT environment variable provide karta hai
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- HELPER FUNCTIONS ---

def is_joined(user_id):
    """Checks if user is a member of the required channel"""
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def clean_response(data):
    """Removes branding and owner info from the JSON response"""
    if isinstance(data, dict):
        # In keys ko output mein nahi dikhaya jayega
        blocked_keys = ['branding', 'owner', 'credit', 'developer', 'status', 'success', 'key_status']

        info_parts = []
        for key, value in data.items():
            if key.lower() not in blocked_keys and value:
                # Key name ko sundar banane ke liye (e.g. 'full_name' -> 'Full Name')
                clean_key = key.replace('_', ' ').title()
                info_parts.append(f"🔹 **{clean_key}**: `{value}`")

        return "\n".join(info_parts) if info_parts else "⚠️ No valid information found."
    return str(data)

# --- BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = message.from_user

    # Owner ko notification bhejna
    log_text = (f"🚀 **New User Alert!**\n\n"
                f"👤 Name: {user.first_name}\n"
                f"🆔 ID: `{user.id}`\n"
                f"🔗 Username: @{user.username if user.username else 'None'}")

    if OWNER_ID:
        try:
            bot.send_message(OWNER_ID, log_text, parse_mode="Markdown")
        except:
            pass

    bot.reply_to(message, "✅ **Bot is active!**\n\nUse me in my official group for OSINT lookups.\nCommands: `/no`, `/vec`, `/tg`", parse_mode="Markdown")

@bot.message_handler(commands=['no', 'vec', 'tg'])
def handle_osint(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    cmd = message.text.split()[0].lower()

    # 1. Force Join Check
    if not is_joined(user_id):
        bot.reply_to(message, f"❌ Aapne channel join nahi kiya hai.\n\nPehle join karein: {CHANNEL_ID}")
        return

    # 2. Group Only Check
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ Ye bot security ki wajah se sirf Groups mein kaam karta hai.")
        return

    # 3. Input Validation
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, f"Usage: `{cmd} [input]`\nExample: `{cmd} 91XXXXXXXXXX`", parse_mode="Markdown")
        return

    query_val = args[1]
    wait_msg = bot.reply_to(message, "🔎 Database se info fetch kar raha hoon... wait.")

    # 4. API Request Setup
    params = {"key": API_KEY}

    if cmd == "/no":
        params.update({"service": "number", "number": query_val})
    elif cmd == "/tg":
        params.update({"service": "tg_to_number", "telegram": query_val})
    elif cmd == "/vec":
        params.update({"service": "vehicle_owner_number", "rc": query_val})

    # 5. Fetching & Cleaning Data
    try:
        response = requests.get(BASE_URL, params=params)

        if response.status_code == 200:
            json_data = response.json()
            # Clean results (remove branding)
            final_info = clean_response(json_data)

            output_msg = f"🔍 **OSINT Result for {query_val}:**\n\n{final_info}"
            bot.edit_message_text(output_msg, chat_id, wait_msg.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ NO DATA FOUND
⟡ All APIs responded but no valid information ⟡.", chat_id, wait_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Error occurred: {str(e)}", chat_id, wait_msg.message_id)

# --- EXECUTION ---
if __name__ == "__main__":
    # Flask ko background thread mein chalayein Render ke liye
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    print("Web Server started on Port 8080. Bot Polling starting...")
    
    # skip_pending=True purane messages ko ignore karta hai (Conflict fix)
    # non_stop=True bot ko band nahi hone deta
    try:
        bot.infinity_polling(skip_pending=True)

    except Exception as e:
        print(f"Polling Error: {e}")
