import os
import threading
import pandas as pd

from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# =========================
# SETTINGS
# =========================
TOKEN = os.getenv("BOT_TOKEN")
EXCEL_PATH = os.getenv("EXCEL_PATH", "base.xlsx")

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
        "/help —
