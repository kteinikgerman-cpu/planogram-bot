import os
import asyncio
import threading
import pandas as pd

from flask import Flask

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters


# =========================
# НАСТРОЙКИ
# =========================
TOKEN = os.getenv("BOT_TOKEN")  # токен берём ТОЛЬКО из Render ENV
EXCEL_PATH = os.getenv("EXCEL_PATH", "base.xlsx")  # файл базы в репозитории

# Flask нужен только для /health (чтобы сервис можно было "пинговать")
app = Flask(__name__)


# =========================
# FLASK (health-check)
# =========================
@app.get("/")
def home():
    return "Planogram bot is running ✅", 200


@app.get("/health")
def health():
    return "ok", 200


# =========================
# EXCEL: читаем базу
# =========================
def load_excel_info() -> str:
    """
    Читает EXCEL_PATH и возвращает короткую информацию.
    Если файла нет — скажет ошибку.
    """
    if not os.path.exists(EXCEL_PATH):
        return f"❌ Excel файл не найден: {EXCEL_PATH}\n" \
               f"Проверь, что он есть в GitHub в корне проекта и называется base.xlsx"

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
    text = (
        "Привет! Я бот ✅\n\n"
        "Я читаю базу автоматически с сервера (Render/GitHub).\n"
        "Команды:\n"
        "/status — проверить базу\n"
        "/help — помощь\n"
    )
    await update.message.reply_text(text)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/status — проверка Excel базы\n\n"
        "Если база не читается — проверь что файл base.xlsx есть в GitHub (в корне проекта)."
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = load_excel_info()
    await update.message.reply_text(info)


async def any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Чтобы бот отвечал хоть как-то (не молчал)
    await update.message.reply_text("✅ Я живой. Напиши /status чтобы проверить базу.")


# =========================
# RUN BOT (polling)
# =========================
async def run_bot():
    if not TOKEN:
        print("❌ BOT_TOKEN пустой! Добавь BOT_TOKEN в Render → Environment.")
        return

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_message))

    print("✅ Telegram bot started (polling)")
    await application.run_polling(close_loop=False)


def start_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"✅ Flask started on port {port}")
    app.run(host="0.0.0.0", port=port)


def main():
    # 1) Flask запускаем в отдельном потоке, чтобы Render видел открытый порт
    threading.Thread(target=start_flask, daemon=True).start()

    # 2) Telegram polling запускаем в asyncio
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
