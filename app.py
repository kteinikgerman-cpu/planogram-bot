import os
import threading
import pandas as pd

from flask import Flask

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# SETTINGS
# =========================
TOKEN = os.getenv("BOT_TOKEN")
EXCEL_PATH = os.getenv("EXCEL_PATH", "base.xlsx")

# Flask app for Render web service + ping
app = Flask(__name__)


# =========================
# FLASK ROUTES
# =========================
@app.get("/")
def home():
    return "Planogram bot is running ✅", 200


@app.get("/health")
def health():
    return "ok", 200


# =========================
# EXCEL
# =========================
def load_excel_info() -> str:
    if not os.path.exists(EXCEL_PATH):
        return (
            f"❌ Excel файл не найден: {EXCEL_PATH}\n"
            f"Проверь, что он лежит в GitHub в корне проекта и называется base.xlsx"
        )

    try:
        df = pd.read_excel(EXCEL_PATH)
        rows, cols = df.shape
        return f"✅ База подключена: {EXCEL_PATH}\n📊 Строк: {rows}\n📌 Колонок: {cols}"
    except Exception as e:
        return f"❌ Не смог прочитать Excel {EXCEL_PATH}\nОшибка: {e}"


# =========================
# TELEGRAM HANDLERS
# =========================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! ✅\n\n"
        "Я читаю Excel базу автоматически с сервера.\n"
        "Команды:\n"
        "/status — проверить базу\n"
        "/help — помощь\n"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/status — проверка Excel базы\n\n"
        "Если база не читается — проверь, что файл base.xlsx есть в GitHub (в корне репозитория)."
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(load_excel_info())


async def any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Я живой. Напиши /status чтобы проверить базу.")


def run_bot_polling():
    """
    Запускаем polling в отдельном потоке.
    Важно: НЕ используем asyncio.run(), чтобы не ловить 'event loop already running'.
    """
    if not TOKEN:
        print("❌ BOT_TOKEN пустой! Добавь BOT_TOKEN в Render → Environment.")
        return

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_message))

    print("✅ Telegram bot started (polling)")
    application.run_polling()


def main():
    # 1) Запускаем Telegram polling в фоне
    threading.Thread(target=run_bot_polling, daemon=True).start()

    # 2) Запускаем Flask в основном потоке (Render ждёт открытый порт)
    port = int(os.environ.get("PORT", 10000))
    print(f"✅ Flask started on port {port}")
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
