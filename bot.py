from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import random
import mysql.connector

BOT_TOKEN = "7256899482:AAFtFnfKfpnGLA3qjBGlKMyVAsVMZ1-AXhw"
# اطلاعات دیتابیس
db_config = {
    "host": "localhost",
    "user": "sgncoir_SGN_TELEGRAM_bot",
    "password": "nGbo1{ew~&$]",
    "database": "sgncoir_SGN_TELEGRAM_bot"
}

# اتصال به دیتابیس
db = mysql.connector.connect(**db_config)
cursor = db.cursor()

# دستورات ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع و ثبت کاربر جدید"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    referrer_id = context.args[0] if context.args else None

    # ثبت کاربر جدید در دیتابیس
    cursor.execute(
        "INSERT IGNORE INTO Users (telegram_id, username) VALUES (%s, %s)",
        (user_id, username)
    )
    db.commit()

    # اگر از لینک دعوت استفاده شده، ثبت دعوت
    if referrer_id:
        try:
            cursor.execute("SELECT id FROM Users WHERE telegram_id = %s", (referrer_id,))
            referrer_db_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO Referrals (user_id, referred_user_id) VALUES (%s, %s)",
                (referrer_db_id, user_id)
            )
            cursor.execute(
                "UPDATE Users SET invites_count = invites_count + 1 WHERE id = %s",
                (referrer_db_id,)
            )
            db.commit()
        except:
            pass

    await update.message.reply_text("سلام! به ربات خوش آمدید.")

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال لینک دعوت اختصاصی"""
    user_id = update.effective_user.id
    invite_link = f"https://t.me/YOUR_BOT_USERNAME?start={user_id}"
    await update.message.reply_text(f"لینک دعوت شما:\n{invite_link}")

async def check_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بررسی تعداد دعوت‌های موفق"""
    user_id = update.effective_user.id
    cursor.execute("SELECT invites_count FROM Users WHERE telegram_id = %s", (user_id,))
    result = cursor.fetchone()

    if result:
        invites_count = result[0]
        if invites_count >= 10:
            # تولید کد تخفیف
            discount_code = f"DISC-{random.randint(1000, 9999)}"
            cursor.execute(
                "INSERT INTO Discounts (user_id, discount_code) VALUES ((SELECT id FROM Users WHERE telegram_id = %s), %s)",
                (user_id, discount_code)
            )
            db.commit()
            await update.message.reply_text(f"تبریک! شما ۱۰ دعوت موفق انجام دادید. کد تخفیف شما:\n{discount_code}")
        else:
            await update.message.reply_text(f"شما {invites_count} نفر دعوت کرده‌اید. برای دریافت کد تخفیف باید ۱۰ نفر را دعوت کنید.")
    else:
        await update.message.reply_text("شما در سیستم ثبت نشده‌اید.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام همگانی توسط ادمین"""
    if update.effective_user.username != "YOUR_ADMIN_USERNAME":
        await update.message.reply_text("شما دسترسی ندارید!")
        return

    message = " ".join(context.args)
    cursor.execute("SELECT telegram_id FROM Users")
    users = cursor.fetchall()

    for (telegram_id,) in users:
        try:
            await context.bot.send_message(chat_id=telegram_id, text=message)
        except:
            pass

    await update.message.reply_text("پیام به همه کاربران ارسال شد.")

async def validate_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اعتبارسنجی کد تخفیف توسط ادمین"""
    if update.effective_user.username != "YOUR_ADMIN_USERNAME":
        await update.message.reply_text("شما دسترسی ندارید!")
        return

    if len(context.args) == 0:
        await update.message.reply_text("لطفاً کد تخفیف را وارد کنید.")
        return

    discount_code = context.args[0]
    cursor.execute("UPDATE Discounts SET is_valid = 0 WHERE discount_code = %s", (discount_code,))
    db.commit()
    await update.message.reply_text(f"کد تخفیف {discount_code} باطل شد.")

# اجرای ربات
if __name__ == "__main__":
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("invite", invite))
    application.add_handler(CommandHandler("check", check_invites))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("validate", validate_discount))

    application.run_polling()
