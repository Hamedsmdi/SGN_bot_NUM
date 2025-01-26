import os
import logging
import psycopg2
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# تنظیمات مربوط به log
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# گرفتن توکن از متغیر محیطی
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# تنظیمات دیتابیس
DB_HOST = "dpg-cub1hu3qf0us73cc12ug-a"
DB_PORT = "5432"
DB_NAME = "telegram_bot_d2me"
DB_USER = "telegram_bot"
DB_PASSWORD = "68IQ9wpq8kRu6prEmd1rKEoDBSpZh4nB"


# تابع اتصال به دیتابیس
def connect_to_database():
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        logger.info("Connected to the database successfully.")
        return connection
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        return None


# ایجاد جدول در دیتابیس (در صورتی که وجود نداشته باشد)
def initialize_database():
    connection = connect_to_database()
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT
                    );
                    """
                )
                connection.commit()
                logger.info("Table 'users' initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing the database: {e}")
        finally:
            connection.close()


# دستور شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("سلام! من یک ربات تلگرام هستم. چگونه می‌توانم کمک کنم؟")


# دستور اضافه کردن اطلاعات کاربر به دیتابیس
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    connection = connect_to_database()

    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING;
                    """,
                    (user.id, user.username, user.first_name, user.last_name),
                )
                connection.commit()
                await update.message.reply_text("اطلاعات شما با موفقیت ذخیره شد!")
        except Exception as e:
            logger.error(f"Error saving user to database: {e}")
            await update.message.reply_text("مشکلی در ذخیره اطلاعات شما پیش آمد.")
        finally:
            connection.close()


# راه‌اندازی برنامه
def main():
    initialize_database()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # اضافه کردن دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("save", save_user))

    # اجرای ربات
    application.run_polling()


if __name__ == "__main__":
    main()
