import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
DB_PATH = os.getenv("DB_PATH", "reviews.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    conn.commit()
    return conn

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь сюда фото или видео на проверку. "
        "После проверки администратор сообщит результат."
    )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Твой Telegram ID: {update.effective_user.id}")

async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    if msg.photo:
        media_type = "photo"
    elif msg.video:
        media_type = "video"
    else:
        await msg.reply_text("Пожалуйста, отправь фото или видео.")
        return

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO submissions (user_id, message_id, status) VALUES (?, ?, 'pending')",
        (user.id, msg.message_id)
    )
    submission_id = cur.lastrowid
    conn.commit()
    conn.close()

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Одобрено", callback_data=f"approve:{submission_id}"),
        InlineKeyboardButton("❌ Отказано", callback_data=f"reject:{submission_id}")
    ]])

    caption = (
        f"Новая заявка №{submission_id}\n"
        f"От: {user.full_name}\n"
        f"ID пользователя: {user.id}\n"
        f"Тип: {media_type}"
    )
    try:
        if msg.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID, photo=msg.photo[-1].file_id,
                caption=caption, reply_markup=keyboard
            )
        else:
            await context.bot.send_video(
                chat_id=ADMIN_ID, video=msg.video.file_id,
                caption=caption, reply_markup=keyboard
            )
        await msg.reply_text("Материал отправлен администратору на проверку.")
    except Exception:
        log.exception("Не удалось отправить заявку администратору")
        conn = db()
        conn.execute("UPDATE submissions SET status='delivery_error' WHERE id=?", (submission_id,))
        conn.commit()
        conn.close()
        await msg.reply_text(
            "Не удалось передать материал администратору. "
            "Проверьте, что администратор открыл бота и нажал /start."
        )

async def decide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("У вас нет доступа.", show_alert=True)
        return

    await query.answer()
    action, raw_id = query.data.split(":", 1)
    submission_id = int(raw_id)

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, status FROM submissions WHERE id=?",
        (submission_id,)
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        await query.edit_message_reply_markup(reply_markup=None)
        return

    user_id, status = row
    if status != "pending":
        conn.close()
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Эта заявка уже обработана.")
        return

    new_status = "approved" if action == "approve" else "rejected"
    cur.execute(
        "UPDATE submissions SET status=? WHERE id=? AND status='pending'",
        (new_status, submission_id)
    )
    changed = cur.rowcount
    conn.commit()
    conn.close()

    if not changed:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Эта заявка уже обработана.")
        return

    if action == "approve":
        user_text = "✅ Твой материал одобрен!"
        admin_text = "✅ Заявка одобрена."
    else:
        user_text = "❌ Твой материал отклонён."
        admin_text = "❌ Заявка отклонена."

    try:
        await context.bot.send_message(chat_id=user_id, text=user_text)
    except Exception:
        log.exception("Не удалось уведомить пользователя %s", user_id)

    try:
        await query.edit_message_caption(
            caption=(query.message.caption or "") + f"\n\n{admin_text}",
            reply_markup=None
        )
    except Exception:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(admin_text)

def main():
    db().close()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, receive_media))
    app.add_handler(CallbackQueryHandler(decide, pattern=r"^(approve|reject):\d+$"))
    app.run_polling()

if __name__ == "__main__":
    main()
