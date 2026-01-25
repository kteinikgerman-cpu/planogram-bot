import os
import threading
import traceback

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
    print(f"[FLASK] starting on port {port}", flush=True)
    app.run(host="0.0.0.0", port=port)

def main():
    print("[MAIN] step 1: starting flask thread", flush=True)
    threading.Thread(target=run_flask, daemon=True).start()

    print("[MAIN] step 2: checking BOT_TOKEN", flush=True)
    if not TOKEN:
        print("[MAIN] BOT_TOKEN is empty -> telegram will NOT start", flush=True)
        return

    print("[MAIN] step 3: building telegram application", flush=True)
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start_cmd))
        application.add_handler(CommandHandler("status", status_cmd))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, any_message))

        print("[TG] Telegram polling started", flush=True)
        application.run_polling()
        print("[TG] polling stopped", flush=True)

    except Exception as e:
        print("[TG] ERROR while starting telegram:", repr(e), flush=True)
        print(traceback.format_exc(), flush=True)

if __name__ == "__main__":
    main()
