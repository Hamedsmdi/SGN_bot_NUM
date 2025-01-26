import os
import logging
import psycopg2
import random
from telegram import Update, ChatMember
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
                        user_id BIGINT NOT NULL UNIQUE,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        invite_count INT DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS discount_codes (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        code VARCHAR(10) NOT NULL UNIQUE,
                        is_used BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                connection.commit()
                logger.info("Tables initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing the database: {e}")
        finally:
            connection.close()


# تولید کد تخفیف به صورت رندوم
def generate_discount_code():
    return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))


# دستور شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("سلام! من ربات هوشمند گالری گوهر نگار هستم. من برای شما یک لینک منحصر به فرد ارسال میکنم و کاربرانی که با این لینک دعوت کنین برای شما امتیاز به همراه میارند و میتونین با امتیازات خودتون تا سقف 50 درصد تخفیف از گالری دریافت کنین ، یعنی اگر سبد خریدتون 1 میلیون تومان بشه شما فقط 500 هزار تومن پرداخت میکنین .")


# ذخیره اطلاعات کاربر در دیتابیس
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


# بررسی عضویت کاربر در کانال
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inviter_user_id = update.effective_user.id
    invite_link = update.message.text.split()[0]  # فرض بر این است که لینک دعوت به صورت مستقیم وارد شده
    invited_user_id = update.message.text.split()[1]  # آیدی کاربری که دعوت شده

    # بررسی عضویت در کانال
    try:
        chat_member = await context.bot.get_chat_member(
            chat_id="@SGN_Gallery_CRM",  # نام کانال شما
            user_id=invited_user_id,
        )

        # اگر عضو شده باشد
        if chat_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
            connection = connect_to_database()
            if connection:
                try:
                    with connection.cursor() as cursor:
                        # افزایش شمارش دعوت‌ها
                        cursor.execute(
                            """
                            UPDATE users
                            SET invite_count = invite_count + 1
                            WHERE user_id = %s
                            RETURNING invite_count;
                            """,
                            (inviter_user_id,)
                        )
                        result = cursor.fetchone()

                        if result:
                            invite_count = result[0]
                            # ارسال پیام به دعوت‌کننده
                            remaining_invites = 10 - invite_count
                            await context.bot.send_message(
                                chat_id=inviter_user_id,
                                text=f"تبریک! عضوی که شما دعوت کرده بودید به کانال پیوست. "
                                     f"شمارش دعوت‌ها به روز شد. شما تاکنون {invite_count} نفر را دعوت کرده‌اید. "
                                     f"فقط {remaining_invites} نفر دیگر دعوت کنید تا کد تخفیف دریافت کنید."
                            )
                except Exception as e:
                    logger.error(f"Error updating invite count: {e}")
            else:
                await update.message.reply_text("مشکلی در اتصال به دیتابیس پیش آمد.")
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        await update.message.reply_text("مشکلی در بررسی عضویت کاربر پیش آمد.")


# شمارش دعوت‌ها و تولید کد تخفیف
async def invite_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("لطفاً آیدی کاربری که دعوت کرده‌اید را وارد کنید.")
        return

    invited_user_id = int(context.args[0])
    inviter_user_id = update.effective_user.id

    connection = connect_to_database()
    if connection:
        try:
            with connection.cursor() as cursor:
                # افزایش شمارش دعوت‌ها
                cursor.execute(
                    """
                    UPDATE users
                    SET invite_count = invite_count + 1
                    WHERE user_id = %s
                    RETURNING invite_count;
                    """,
                    (inviter_user_id,)
                )
                result = cursor.fetchone()

                if result:
                    invite_count = result[0]
                    if invite_count >= 10:
                        discount_code = generate_discount_code()
                        cursor.execute(
                            """
                            INSERT INTO discount_codes (user_id, code)
                            VALUES (%s, %s);
                            """,
                            (inviter_user_id, discount_code),
                        )
                        await update.message.reply_text(
                            f"تبریک! شما ۱۰ نفر دعوت کرده‌اید. کد تخفیف شما: {discount_code}"
                        )
                connection.commit()
        except Exception as e:
            logger.error(f"Error updating invite count: {e}")
            await update.message.reply_text("مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")
        finally:
            connection.close()


# ارسال پیام انبوه
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != 123456789:  # جایگزین با آیدی ادمین
        await update.message.reply_text("شما دسترسی لازم برای این دستور را ندارید.")
        return

    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("لطفاً پیام موردنظر را وارد کنید.")
        return

    connection = connect_to_database()
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users")
                users = cursor.fetchall()
                for user in users:
                    try:
                        await context.bot.send_message(chat_id=user[0], text=message)
                    except Exception as e:
                        logger.error(f"Failed to send message to {user[0]}: {e}")
        finally:
            connection.close()


# راه‌اندازی برنامه
def main():
    initialize_database()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # اضافه کردن دستورات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("save", save_user))
    application.add_handler(CommandHandler("invite", invite_user))
    application.add_handler(CommandHandler("broadcast", broadcast))

    # اجرای ربات
    application.run_polling()


if __name__ == "__main__":
    main()
