import psycopg2
from psycopg2 import sql
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# تنظیمات اتصال به دیتابیس
db_config = {
    'host': 'dpg-cub1hu3qf0us73cc12ug-a',
    'port': '5432',
    'dbname': 'telegram_bot_d2me',
    'user': 'telegram_bot',
    'password': '68IQ9wpq8kRu6prEmd1rKEoDBSpZh4nB'
}

# ایجاد جدول در دیتابیس
def initialize_database():
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT NOT NULL,
            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255),
            username VARCHAR(255),
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
        cursor.execute(create_table_query)
        conn.commit()
        print("Table 'users' initialized successfully")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error initializing database: {e}")

# ذخیره اطلاعات کاربر در دیتابیس
def save_user_to_db(telegram_id, first_name, last_name, username):
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        insert_query = '''
        INSERT INTO users (telegram_id, first_name, last_name, username)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (telegram_id) DO NOTHING
        '''
        cursor.execute(insert_query, (telegram_id, first_name, last_name, username))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error saving user to database: {e}")

# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_to_db(
        telegram_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username
    )
    await update.message.reply_text(f"سلام {user.first_name}! به ربات ما خوش آمدید.")

# دستور /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لیست دستورات موجود:\n/start - شروع\n/help - کمک")

# تابع اصلی
def main():
    # مقداردهی اولیه دیتابیس
    initialize_database()

    # ساخت اپلیکیشن ربات
    application = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    # اضافه کردن دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # اجرا
    application.run_polling()

if __name__ == "__main__":
    main()
