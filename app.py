import os
import threading
import pandas as pd

from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
EXCEL_PATH = os.getenv("EXCEL_PATH", "base.xlsx")

app = Flask(__name__)

@app.get("/")
def home():
    return "OK", 200

@app.get("/health")
def health():
    return "ok", 200

def load_excel_info() -> str:
    if not os.path.exists(EXCEL_PATH):
        return f"Excel not found: {EXCEL_PATH}"

    try:
        df = pd.read_excel(EXCEL_PATH)
        return f"Excel OK: {EXCEL_PATH} rows={df.shape[0]} cols={df.shape[1]}"
    except Exception as e:
        return f"Excel read error: {e}"

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot OK. Use /status")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(load_excel_info())

async def any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("OK. Use /status")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"Flask on port {port}")
    app.run(host="0.0.0.0", port=port)

def main():
    # Flask thread
    threading.Thread(target=run_flask, daemon=True).start()

    # Telegram polling in main thread
    if not TOKEN:
        print("BOT_TOKEN is empty")
        return

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_message))

    print("Telegram polling started")
    application.run_polling()

if __name__ == "__main__":
    main()
