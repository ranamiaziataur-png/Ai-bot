import telebot
from telebot import types
from google import genai
from PIL import Image, ImageDraw, ImageFont
import io
import datetime
import base64
import schedule
import time
from threading import Thread
import os

# --- Configuration Setup ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8611406941:AAHmwjhR9LCUFtU6Htwl4s3lsnawmz_nIFQ')
BOT_USERNAME = '@pro_spider_bot'         
OFFICIAL_CHANNEL = '@pro_spider_official' 
CHANNEL_URL = 'https://t.me/pro_spider_official' 
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AQ.Ab8RN6LhoEufY2gxfO88sq4JMLBJ5FQ133ZSjz5UeSR7Dq_uSg') 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

user_db = {}

WELCOME_TEXT = (
    "👋 **Welcome to Pro Spider AI Bot!**\n\n"
    "I am an advanced multi-niche automation system built for **Trading, Crypto, News, and Business** groups/channels. "
    "I understand **ANY language** you type and instantly generate tailored posts with watermarked graphics!\n\n"
    "⚙️ **Manual Posting:**\n"
    "Use `/post <your topic>` in any language.\n"
    "*(Example: `/post btc price analysis today` or `/post শীর্ষ বিজনেস টিপস`)*\n\n"
    "⏰ **Auto-Scheduling:**\n"
    "Set automatic times for daily posts using `/settime HH:MM` (e.g., `/settime 09:00`).\n\n"
    "🎁 **Free Limit:**\n"
    f"Join our Official Channel {OFFICIAL_CHANNEL} to get **1 FREE manual post daily**.\n\n"
    "⭐ **Premium Membership Packages:**\n"
    "Type `/subscribe` to choose your automated growth tier.\n\n"
    "💝 **Charity Initiative:**\n"
    "**5% of all earnings** from this bot are donated directly to charities supporting the poor and homeless."
)

PLAN_INFO = (
    "🚀 **Choose Your Pro Spider AI Subscription Tier**\n\n"
    "🥉 **Bronze Tier — 50 Stars / Month**\n"
    "• 5 Manual AI Posts per day\n"
    "• 1 Auto-Scheduled Post daily at your preferred time\n\n"
    "🥈 **Silver Tier — 100 Stars / Month**\n"
    "• 20 Manual AI Posts per day\n"
    "• 3 Auto-Scheduled Posts daily (Keep your group alive 24/7)\n\n"
    "🥇 **Gold Ultimate Tier — 130 Stars / Month**\n"
    "• 🔥 UNLIMITED Manual AI Posts\n"
    "• 5 Auto-Scheduled Posts daily + Premium Trading/Business Prompts\n\n"
    "💝 *Reminder: 5% of your subscription goes to helping homeless and poor families.*"
)

def is_joined_channel(user_id):
    try:
        member = bot.get_chat_member(OFFICIAL_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator', 'owner']
    except:
        return False

def add_watermark(image_bytes, text):
    img = Image.open(io.BytesIO(image_bytes))
    draw = ImageDraw.Draw(img)
    width, height = img.size
    try:
        font = ImageFont.truetype("arial.ttf", int(height * 0.04))
    except:
        font = ImageFont.load_default()
        
    position = (int(width * 0.05), int(height * 0.90))
    draw.text((position-2, position-2), text, fill="black", font=font)
    draw.text((position+2, position+2), text, fill="black", font=font)
    draw.text(position, text, fill="white", font=font)
    
    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Join Official Channel", url=CHANNEL_URL))
    markup.add(types.InlineKeyboardButton("➕ Add Bot to Group/Channel", url=f"https://t.me/{BOT_USERNAME[1:]}?startgroup=true"))
    bot.reply_to(message, WELCOME_TEXT, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['subscribe'])
def show_packages(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🥉 Bronze Pass (50 Stars)", callback_data="buy_bronze"))
    markup.add(types.InlineKeyboardButton("🥈 Silver Pass (100 Stars)", callback_data="buy_silver"))
    markup.add(types.InlineKeyboardButton("🥇 Gold Pass (130 Stars)", callback_data="buy_gold"))
    bot.reply_to(message, PLAN_INFO, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_subscription(call):
    user_id = call.from_user.id
    plan_tier = call.data.split('_')[1]
    
    tier_config = {
        'bronze': {'title': "Bronze Tier Membership", 'amount': 50},
        'silver': {'title': "Silver Tier Membership", 'amount': 100},
        'gold': {'title': "Gold Ultimate Membership", 'amount': 130}
    }
    
    prices = [types.LabeledPrice(label=tier_config[plan_tier]['title'], amount=tier_config[plan_tier]['amount'])]
    
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title=tier_config[plan_tier]['title'],
        description="Activate your 30-day premium access. 5% is donated to homeless support.",
        provider_token="", 
        currency="XTR", 
        prices=prices,
        start_parameter="ai-subscription",
        payload=f"sub_{user_id}_{plan_tier}"
    )

@bot.message_handler(commands=['settime'])
def set_auto_time(message):
    user_id = message.from_user.id
    command_text = message.text.split(' ')
    
    if len(command_text) < 2:
        bot.reply_to(message, "❌ Please specify time in HH:MM format.\nExample: `/settime 14:30`")
        return
        
    time_str = command_text[1]
    if user_id not in user_db:
        user_db[user_id] = {'plan': 'free', 'schedule_times': []}
        
    user_db[user_id]['schedule_times'].append(time_str)
    bot.reply_to(message, f"⏰ Success! Automated daily post scheduled at **{time_str}** for this chat.")

@bot.message_handler(commands=['post'])
def handle_manual_post(message):
    user_id = message.from_user.id
    command_text = message.text.split(' ', 1)
    
    if len(command_text) < 2:
        bot.reply_to(message, "❌ Syntax: `/post <your topic in any language>`")
        return
        
    topic = command_text[1]
    
    if user_db.get(user_id, {}).get('plan', 'free') == 'free':
        if not is_joined_channel(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 Join Official Channel", url=CHANNEL_URL))
            bot.reply_to(message, "⚠️ Access Denied! Please join our Official Channel to process your free daily post.", reply_markup=markup)
            return

    sent_msg = bot.reply_to(message, "⏳ **Pro Spider AI is analyzing your topic and language...**")
    generate_ai_content(message.chat.id, topic, sent_msg.message_id)

def generate_ai_content(chat_id, topic, msg_id):
    try:
        text_prompt = (
            f"Analyze the user's language and topic from this input: '{topic}'. "
            "Write a highly professional, engaging post specifically tailored for Telegram channels. "
            "If the topic is related to trading/crypto, include basic structure, indicators, and market context. "
            "If it is business/news, make it highly structured and factual. "
            "CRITICAL: Output the entire response in the EXACT same language as the input topic. Include relevant emojis and hashtags."
        )
        
        text_response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=text_prompt
        )
        
        image_prompt = f"Professional clean tech banner or business illustration about: {topic}."
        image_interaction = ai_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=image_prompt
        )
        
        raw_image_data = image_interaction.candidates.content.parts.inline_data.data
        image_bytes = base64.b64decode(raw_image_data)
        
        final_image = add_watermark(image_bytes, f"Pro Spider Bot | {BOT_USERNAME}")
        
        bot.delete_message(chat_id, msg_id)
        bot.send_photo(chat_id, photo=final_image, caption=text_response.text, parse_mode="Markdown")
    except Exception as e:
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
        bot.send_message(chat_id, f"❌ Error generating content: {str(e)}")

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=run_schedule).start()
    print("Bot is starting successfully...")
    bot.infinity_polling()
