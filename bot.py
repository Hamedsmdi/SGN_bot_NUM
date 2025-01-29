import os
import logging
import random
import psycopg2
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# تنظیمات مربوط به log
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# گرفتن مقادیر حساس از متغیرهای محیطی
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # نام کاربری کانال (مثلاً @yourchannel)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# تنظیم Flask
app = Flask(__name__)

def connect_to_database():
    try:
        return psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def initialize_database():
    connection = connect_to_database()
    if connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    invite_count INT DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS discount_codes (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    code VARCHAR(5) NOT NULL UNIQUE,
                    is_used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            connection.commit()
        connection.close()

def generate_discount_code():
    return ''.join(random.choices('0123456789', k=5))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    invite_link = f"https://t.me/{context.bot.username}?start={user.id}"
    
    connection = connect_to_database()
    if connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (user_id, username, first_name, last_name) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING;",
                (user.id, user.username, user.first_name, user.last_name)
            )
            connection.commit()
        connection.close()
    
    await update.message.reply_text(
        f"سلام {user.first_name}!\n\n"
        "📢 برای دریافت کد تخفیف ۱۵٪، دوستان خود را به کانال ما دعوت کنید!\n"
        "🎁 به ازای هر ۵ نفر که از طریق لینک شما عضو شوند، یک کد تخفیف دریافت می‌کنید.\n\n"
        f"🔗 لینک دعوت شما: {invite_link}"
    )

async def check_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    member_status = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
    
    if member_status.status in ['member', 'administrator', 'creator']:
        connection = connect_to_database()
        if connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT invite_count FROM users WHERE user_id = %s;", (user_id,))
                result = cursor.fetchone()
                invite_count = result[0] if result else 0
                
                await update.message.reply_text(f"📊 تعداد دعوت‌های شما: {invite_count}")
            connection.close()
    else:
        await update.message.reply_text("🚫 شما هنوز عضو کانال نیستید! لطفاً ابتدا در کانال عضو شوید.")

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("❌ لطفاً آیدی فرد دعوت‌کننده را ارسال کنید!")
        return
    
    inviter_id = int(context.args[0])
    invited_id = update.effective_user.id
    
    connection = connect_to_database()
    if connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s;", (invited_id,))
            if cursor.fetchone():
                await update.message.reply_text("⚠️ شما قبلاً ثبت شده‌اید!")
                connection.close()
                return
            
            cursor.execute(
                "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING;",
                (invited_id,)
            )
            cursor.execute(
                "UPDATE users SET invite_count = invite_count + 1 WHERE user_id = %s RETURNING invite_count;",
                (inviter_id,)
            )
            result = cursor.fetchone()
            invite_count = result[0] if result else 0
            
            if invite_count % 5 == 0:
                discount_code = generate_discount_code()
                cursor.execute("INSERT INTO discount_codes (user_id, code) VALUES (%s, %s);", (inviter_id, discount_code))
                await context.bot.send_message(inviter_id, f"🎉 تبریک! شما ۵ نفر دعوت کردید. کد تخفیف شما: {discount_code}")
            connection.commit()
        connection.close()
        await update.message.reply_text("✅ دعوت شما ثبت شد!")

def setup_telegram_bot():
    initialize_database()
    bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("invite", invite))
    bot.add_handler(CommandHandler("check", check_invite))
    
    return bot

tg_bot = setup_telegram_bot()

@app.route("/")
def home():
    return "ربات تلگرام فعال است!"

async def process_update(update_data):
    update = Update.de_json(update_data, tg_bot.bot)
    await tg_bot.update_queue.put(update)

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update_data = request.get_json(force=True)
    asyncio.create_task(process_update(update_data))
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8443)
