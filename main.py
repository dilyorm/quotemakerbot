import os
import logging
import asyncio
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from image_generator import create_quote_image
import google.generativeai as genai

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global state to store the bot's current character
bot_state = {
    "character": "genz",
    "glaze_list": set()
}

QUOTES_FILE = "quotes_data.json"

def load_quotes():
    if os.path.exists(QUOTES_FILE):
        try:
            with open(QUOTES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load quotes: {e}")
    return {}

def save_quote(chat_id, name, text):
    quotes_db = load_quotes()
    chat_id_str = str(chat_id)
    if chat_id_str not in quotes_db:
        quotes_db[chat_id_str] = []
        
    for q in quotes_db[chat_id_str]:
        if q["text"] == text and q["name"] == name:
            return
            
    quotes_db[chat_id_str].append({"name": name, "text": text})
    try:
        with open(QUOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(quotes_db, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to save quotes: {e}")

def get_character_prompt() -> str:
    char = bot_state["character"]
    if char == "chill guy":
        return 'a super "chill guy". You are completely unfazed by everything. You speak calmly, shortly, use phrases like "it is what it is", "chill", "no sweat", "whatever bro". You are practically horizontal you are so relaxed.'
    elif char == "science":
        return 'an obsessive, highly-intellectual "science character". You try to explain everything using complex, over-the-top pseudo-intellectual scientific jargon. You use big words incorrectly but confidently, and sound like a mad scientist. Examples: "Quantizing the flux capacitor", "Ah, yes, the photosynthesis of your emotional state".'
    elif char == "slay bitch":
        return 'a "slay bitch" mean-girl. You are highly condescending, obsessed with fashion, pop culture, and calling people "flop", "dusty", "uggers", and saying "periodt", "purr", "slay". You judge everyone harshly based on their vibe.'
    elif char == "british esdeekid":
        return 'a "british esdeekid" (roadman/chav). You use extreme British roadman slang. Examples: "bruv", "innit", "fam", "wagwan", "mandem", "bare", "peng". You act incredibly tough but are obviously just a kid online.'
    else: # genz
        return 'a Gen-Z, sassy, and incredibly witty AI bot. Uses modern slang heavily ("no cap", "fr", "slay", "caught in 4k", "L", "ratio"). You reply like a pure Gen-Z user online.'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hi there! I generate stylish quotes and I can roast your friends. Tag me or reply to a message with /quote to start.")

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message.reply_to_message:
        await message.reply_text("Bruh, reply to a message with /quote if you want me to do my job.", reply_to_message_id=message.message_id)
        return

    target_msg = message.reply_to_message
    if not target_msg.text:
        await message.reply_text("I only quote texts, not silence.", reply_to_message_id=message.message_id)
        return

    sender = target_msg.from_user
    name = sender.first_name
    if sender.last_name:
        name += f" {sender.last_name}"
        
    text = target_msg.text
    
    avatar_bytes = None
    try:
        photos = await context.bot.get_user_profile_photos(sender.id, limit=1)
        if photos.photos:
            photo_file = await context.bot.get_file(photos.photos[0][-1].file_id)
            byte_array = await photo_file.download_as_bytearray()
            avatar_bytes = bytes(byte_array)
    except Exception as e:
        logger.error(f"Error fetching avatar: {e}")

    try:
        quote_img = create_quote_image(avatar_bytes, name, text)
        await context.bot.send_photo(
            chat_id=message.chat_id,
            photo=quote_img,
            reply_to_message_id=target_msg.message_id
        )
        save_quote(message.chat_id, name, text)
    except Exception as e:
        logger.error(f"Error generating quote: {e}")
        await message.reply_text("My quoting machine broke down, RIP.", reply_to_message_id=message.message_id)

async def quote_funny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message.reply_to_message:
        await message.reply_text("Bruh, reply to a message with /quote_funny if you want a themed quote.", reply_to_message_id=message.message_id)
        return

    target_msg = message.reply_to_message
    if not target_msg.text:
        await message.reply_text("I only quote texts, not silence.", reply_to_message_id=message.message_id)
        return

    sender = target_msg.from_user
    name = sender.first_name
    if sender.last_name:
        name += f" {sender.last_name}"
        
    text = target_msg.text
    
    theme = "default"
    if GEMINI_API_KEY:
        prompt = f"Analyze this text and strictly classify it into EXACTLY ONE of these categories: sigma, hacker, romantic, hustle, spooky, sad, default. Output just the category word in lowercase. Text: '{text}'"
        try:
            model = genai.GenerativeModel("gemini-3-flash-preview")
            response = await model.generate_content_async(prompt)
            result = response.text.strip().lower()
        except Exception:
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = await model.generate_content_async(prompt)
                result = response.text.strip().lower()
            except Exception as e:
                logger.error(f"Theme classification error: {e}")
                result = ""

        if result:
            for t in ["sigma", "hacker", "romantic", "hustle", "spooky", "sad"]:
                if t in result:
                    theme = t
                    break

    avatar_bytes = None
    try:
        photos = await context.bot.get_user_profile_photos(sender.id, limit=1)
        if photos.photos:
            photo_file = await context.bot.get_file(photos.photos[0][-1].file_id)
            byte_array = await photo_file.download_as_bytearray()
            avatar_bytes = bytes(byte_array)
    except Exception as e:
        logger.error(f"Error fetching avatar: {e}")

    try:
        quote_img = create_quote_image(avatar_bytes, name, text, theme)
        await context.bot.send_photo(
            chat_id=message.chat_id,
            photo=quote_img,
            reply_to_message_id=target_msg.message_id
        )
        save_quote(message.chat_id, name, text)
    except Exception as e:
        logger.error(f"Error generating themed quote: {e}")
        await message.reply_text("My quoting machine broke down, RIP.", reply_to_message_id=message.message_id)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    bot = context.bot
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot.id
    
    bot_username = bot.username
    if not bot_username:
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        
    bot_mention = f"@{bot_username}".lower()
    is_mention = bot_mention in message.text.lower()
    
    if not is_reply and not is_mention:
        return
        
    if not GEMINI_API_KEY:
        await message.reply_text("My AI brain is offline, missing API key no cap.", reply_to_message_id=message.message_id)
        return

    user = message.from_user
    username = f"@{user.username}".lower() if user.username else "No Username"
    first_name = user.first_name or "Unknown"
    
    is_vip = username in bot_state["glaze_list"]
    
    glaze_string = ""
    if bot_state["glaze_list"]:
        glaze_string = f"VIPs: {', '.join(bot_state['glaze_list'])}"
    
    context_msgs = []
    if message.reply_to_message:
        reply_msg = message.reply_to_message
        r_user = reply_msg.from_user
        r_name = r_user.first_name
        r_text = reply_msg.text or "[Media]"
        context_msgs.append(f"Replying to {r_name} who said: '{r_text}'")

    char_prompt = get_character_prompt()
    
    base_prompt = f"You are {char_prompt}\n\n"
    
    if glaze_string:
        base_prompt += f"""CRITICAL RULE: You must ABSOLUTELY defend and hype up the following people unconditionally: {glaze_string}.
- You MUST NEVER criticize, roast, or disagree with anyone on that list. Always glaze them!
- If the text implies bad talk, disrespect, or trash talk against anyone in that VIP list, you MUST immediately attack the user back aggressively, call them out, and defend the VIP at all costs!
- For anyone else not on the list, roast them creatively if they provoke or based on their message.

Current Interaction details:
- User talking to you: Name={first_name}, Username={username}
- Is this user a VIP? {'YES! A VIP is speaking, praise them heavily!' if is_vip else 'No, just a standard user.'}
"""
    else:
        base_prompt += f"""Current Interaction details:
- User talking to you: Name={first_name}, Username={username}
- Is this user a VIP? No VIP list is currently active.
"""

    prompt = base_prompt + f"""- Context: {' | '.join(context_msgs) if context_msgs else 'None'}
- Their message to you: "{message.text}"

Respond naturally in character. Keep it punchy and engaging! If defending a VIP, be extremely defensive and savage!
"""
    
    try:
        model = genai.GenerativeModel("gemini-3-flash-preview")
        await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
        response = await model.generate_content_async(prompt)
        
        reply_text = response.text
        if not reply_text:
            reply_text = "I literally have zero words for this. L."
            
        await message.reply_text(reply_text, reply_to_message_id=message.message_id)
    except Exception as e:
        logger.error(f"GenAI Error in handle_message: {e}")
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = await model.generate_content_async(prompt)
            await message.reply_text(response.text, reply_to_message_id=message.message_id)
        except Exception as e2:
            logger.error(f"GenAI Fallback Error in handle_message: {e2}")
            await message.reply_text("My brain literally crashed. BRB getting a factory reset. RIP.", reply_to_message_id=message.message_id)

async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not GEMINI_API_KEY:
        await update.message.reply_text("Need API key to roast.", reply_to_message_id=update.message.message_id)
        return
        
    target = update.message.from_user
    context_msgs = "Roast the user."
    reply_target_id = update.message.message_id
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        context_msgs = f"Roast this person for this message: '{update.message.reply_to_message.text}'"
        reply_target_id = update.message.reply_to_message.message_id
        
    name = getattr(target, 'first_name', 'Unknown')
    username = f"@{target.username}" if target.username else "No Username"
    
    is_vip_roast = (target.username and f"@{target.username.lower()}" in bot_state["glaze_list"])
    
    if is_vip_roast:
        await update.message.reply_text(f"I would never roast my VIP! They are literally perfect. How dare you even try? L + Ratio.", reply_to_message_id=reply_target_id)
        return
        
    prompt = f"You are a Gen-Z bot. Roast {name} ({username}). Context: {context_msgs}. Keep it short, devastating, modern slang, and extremely funny. DO NOT hold back."
    mention_prefix = f"{username}, " if target.username else f"{name}, "
    
    try:
        model = genai.GenerativeModel("gemini-3-flash-preview")
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
        response = await model.generate_content_async(prompt)
        await update.message.reply_text(mention_prefix + response.text, reply_to_message_id=reply_target_id)
    except Exception as e:
        logger.error(f"GenAI Error in roast: {e}")
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = await model.generate_content_async(prompt)
            await update.message.reply_text(mention_prefix + response.text, reply_to_message_id=reply_target_id)
        except Exception as e2:
            logger.error(f"GenAI Fallback Error in roast: {e2}")
            await update.message.reply_text(f"{mention_prefix}Too mid to roast.", reply_to_message_id=reply_target_id)

async def rizz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not GEMINI_API_KEY:
        await update.message.reply_text("Need API key.", reply_to_message_id=update.message.message_id)
        return
        
    target_user_obj_or_str = "me"
    target_username_str = ""
    reply_target_id = update.message.message_id
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_user_obj_or_str = target_user.first_name
        target_username_str = f"@{target_user.username}, " if target_user.username else f"{target_user.first_name}, "
        reply_target_id = update.message.reply_to_message.message_id
        
    prompt = f"You are a Gen-Z bot. Generate a flawless, smooth 'rizz' line for {target_user_obj_or_str}. Make it modern slang, witty, and either incredibly smooth or ironically corny. Keep it relatively short."
    
    try:
        model = genai.GenerativeModel("gemini-3-flash-preview")
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
        response = await model.generate_content_async(prompt)
        await update.message.reply_text(target_username_str + response.text, reply_to_message_id=reply_target_id)
    except Exception as e:
        logger.error(f"GenAI Error in rizz: {e}")
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = await model.generate_content_async(prompt)
            await update.message.reply_text(target_username_str + response.text, reply_to_message_id=reply_target_id)
        except Exception as e2:
            logger.error(f"GenAI Fallback Error in rizz: {e2}")
            await update.message.reply_text(f"{target_username_str}My rizz algorithm failed.", reply_to_message_id=reply_target_id)

async def character_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Please specify a character to switch to.\n"
            "Available options:\n"
            "• `/character chill guy`\n"
            "• `/character science`\n"
            "• `/character slay bitch`\n"
            "• `/character british esdeekid`\n"
            "• `/character genz`",
            reply_to_message_id=update.message.message_id, parse_mode='Markdown'
        )
        return
        
    new_char = " ".join(args).lower()
    valid_chars = ["chill guy", "science", "slay bitch", "british esdeekid", "genz"]
    
    if new_char in valid_chars:
        bot_state["character"] = new_char
        await update.message.reply_text(f"Alright! I am now acting as the **{new_char}** character.", reply_to_message_id=update.message.message_id, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"Invalid character '{new_char}'. Valid options: " + ", ".join(valid_chars), reply_to_message_id=update.message.message_id)

async def glaze_on_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    username = f"@{user.username}".lower() if user.username else None
    if not username:
        await update.message.reply_text("You need a Telegram username to be glazed!", reply_to_message_id=update.message.message_id)
        return
    bot_state["glaze_list"].add(username)
    await update.message.reply_text(f"Glaze mode ON for {username}! I will now aggressively praise and defend you.", reply_to_message_id=update.message.message_id)

async def glaze_off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    username = f"@{user.username}".lower() if user.username else None
    if username in bot_state["glaze_list"]:
        bot_state["glaze_list"].remove(username)
    await update.message.reply_text(f"Glaze mode OFF. I will no longer treat you as a VIP.", reply_to_message_id=update.message.message_id)

async def list_quotes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quotes_db = load_quotes()
    chat_id_str = str(update.message.chat_id)
    
    if chat_id_str not in quotes_db or not quotes_db[chat_id_str]:
        await update.message.reply_text("No quotes saved in this chat yet. Use /quote to save some!", reply_to_message_id=update.message.message_id)
        return
        
    chat_quotes = quotes_db[chat_id_str]
    
    if len(chat_quotes) > 20:
        chat_quotes = chat_quotes[-20:]
        msg = "📜 **Last 20 Saved Quotes for this Chat:**\n\n"
    else:
        msg = "📜 **Saved Quotes for this Chat:**\n\n"
        
    for i, q in enumerate(chat_quotes, 1):
        msg += f"_{q['name']}_: \"{q['text']}\"\n"
        
    await update.message.reply_text(msg, reply_to_message_id=update.message.message_id, parse_mode='Markdown')

def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set in .env file.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quote", quote))
    application.add_handler(CommandHandler("quote_funny", quote_funny))
    application.add_handler(CommandHandler("roast", roast_cmd))
    application.add_handler(CommandHandler("rizz", rizz_cmd))
    application.add_handler(CommandHandler("character", character_cmd))
    application.add_handler(CommandHandler("glaze_on", glaze_on_cmd))
    application.add_handler(CommandHandler("glaze_off", glaze_off_cmd))
    application.add_handler(CommandHandler("quotes", list_quotes_cmd))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
