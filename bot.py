import logging
import os
import random
import psycopg2
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
from telegram.ext import PicklePersistence
from telegram.ext import ApplicationBuilder

# اطلاعات مربوط به محیط
PORT = os.getenv("PORT", "80")
DATABASE_URL = os.getenv("DATABASE_URL", "YOUR_DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://sgn-bot-num.onrender.com/")

# راه‌اندازی لاگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# اتصال به دیتابیس
def connect_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# ارسال پیام خوشامدگویی به کاربر پس از اجرای دستور /start
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    invite_link = f"https://t.me/{context.bot.username}?start={user_id}"

    # ارسال لینک دعوت به کاربر
    await update.message.reply_text(f"سلام! برای دعوت از دوستان خود به کانال فروشگاه، از لینک زیر استفاده کنید:\n{invite_link}")

    # ثبت کاربر در دیتابیس
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

# ثبت عضویت جدید
async def new_member(update: Update, context: CallbackContext):
    for member in update.message.new_chat_members:
        user_id = member.id
        inviter_id = update.message.from_user.id

        # اتصال به دیتابیس برای شمارش تعداد دعوت‌ها
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE inviter_id = %s", (inviter_id,))
        count = cursor.fetchone()[0]

        if count == 9:  # چک کردن که کاربر 10 نفر دعوت کرده باشد
            discount_code = generate_discount_code()
            await context.bot.send_message(inviter_id, f"تبریک! شما 10 نفر را به کانال دعوت کرده‌اید. کد تخفیف شما: {discount_code}")

        # اطلاع‌رسانی به کاربر
        await context.bot.send_message(inviter_id, f"{member.full_name} به کانال پیوست.\nتعداد افرادی که شما دعوت کرده‌اید: {count + 1} نفر")

        cursor.close()
        conn.commit()
        conn.close()

# تولید کد تخفیف رندوم
def generate_discount_code():
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))

# راه‌اندازی Webhook و اجرای برنامه
async def main():
    # راه‌اندازی برنامه
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # اضافه کردن handler‌ها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))

    # شروع Webhook
    application.run_webhook(
        listen="0.0.0.0",  # گوش دادن به همه IP‌ها
        port=int(PORT),  # پورت اختصاصی
        url_path=TELEGRAM_BOT_TOKEN,
        webhook_url=WEBHOOK_URL,  # دامنه Render شما
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
