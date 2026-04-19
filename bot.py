import os
import telebot
import requests
from telebot import types

# --- LOAD ENVIRONMENT VARIABLES ---
# In Render, you must add these keys in the "Environment" tab
TOKEN = os.getenv('BOT_TOKEN')
# The full API base including the prefix before the number
API_BASE_URL = os.getenv('API_BASE_URL') # https://say-wallahai-bro-say-wallahi.onrender.com/raavan/v34/query=
# The API key part
API_KEY_PART = os.getenv('API_KEY')      # /key=RATELIMITE-BEIBBkim7bjTAkJIZTIUGPR4FkfNAYoj
# Channel Numeric ID (Starts with -100)
CHANNEL_ID = os.getenv('CHANNEL_ID') 
CHANNEL_LINK = "https://t.me/+K1rF0W7od_wyNjVl"

bot = telebot.TeleBot(TOKEN)

# Simple dictionary to store basic user history if needed
user_sessions = {}

def check_join(user_id):
    """Verifies if the user is a member of the required channel."""
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"Error checking channel join: {e}")
        # If bot is not admin in channel, this check might fail
        return False

@bot.message_handler(commands=['start'])
def start_cmd(message):
    # RULE: Only work in groups
    if message.chat.type == 'private':
        bot.reply_to(message, "❌ **Access Denied!**\nThis bot only works inside Groups. Add me to a group and make me admin to start searching.")
        return
    
    user_sessions[message.from_user.id] = "started"
    bot.reply_to(message, "✅ **Lulzsec OSINT Bot Active**\n\nSend `/num <10-digit-number>` to begin.\nExample: `/num 9876543210`")

@bot.message_handler(commands=['num'])
def handle_search(message):
    # 1. Group Check
    if message.chat.type == 'private':
        bot.reply_to(message, "❌ Please use this bot in a Group.")
        return

    # 2. Force Join Check
    if not check_join(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Join Channel 📢", url=CHANNEL_LINK)
        markup.add(btn)
        bot.reply_to(message, "🚫 **Join Required!**\n\nYou must be a member of our channel to use this search bot.", reply_markup=markup)
        return

    # 3. Input Validation
    text_parts = message.text.split()
    if len(text_parts) < 2:
        bot.reply_to(message, "❗ **Usage:** `/num 9723700508` (10 digits without +91)")
        return

    raw_input = text_parts[1]
    # Extract last 10 digits to ensure no +91 interference
    clean_number = "".join(filter(str.isdigit, raw_input))[-10:]

    if len(clean_number) != 10:
        bot.reply_to(message, "❌ Invalid format. Provide a 10-digit Indian number.")
        return

    # 4. API Request
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Construct URL using environment variables
        # Format: BaseURL + 91 + Number + KeyPart
        api_url = f"{API_BASE_URL}91{clean_number}{API_KEY_PART}"
        
        response = requests.get(api_url, timeout=20)
        
        if response.status_code == 200:
            # We assume response is text or JSON. If text, we wrap in code block.
            api_data = response.text
            
            # Format Result
            response_msg = f"🔍 **Search Result for {clean_number}:**\n\n"
            response_msg += f"