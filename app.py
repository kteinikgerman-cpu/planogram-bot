import os
import re
import threading
import pandas as pd
from flask import Flask, Response

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# НАСТРОЙКИ / ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_FILE = "db.xlsx"

# ADMIN_ID можно хранить в Render → Environment (рекомендую)
# если не задан — загрузка Excel будет недоступна
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")

REQUIRED_COLUMNS = [
    "EAN", "SAP", "Название", "Ряд", "Стеллаж", "Полка", "Позиция", "Фейсинг", "Упаковка"
]

df_cache: pd.DataFrame | None = None

# =========================
# PUBLIC WEBAPP URL
# =========================
def guess_public_url_from_replit() -> str:
    # Для Replit (если вдруг используешь)
    if os.getenv("REPLIT_DEV_DOMAIN"):
        return "https://" + os.getenv("REPLIT_DEV_DOMAIN").strip()

    if os.getenv("REPLIT_DOMAINS"):
        dom = os.getenv("REPLIT_DOMAINS").split(",")[0].strip()
        if dom:
            return "https://" + dom

    return ""

# Главное: сначала берём из ENV (Render), иначе пробуем угадать (Replit)
PUBLIC_WEBAPP_URL = (os.getenv("PUBLIC_WEBAPP_URL", "").strip()
                     or guess_public_url_from_replit())

# =========================
# FLASK WEB SERVER (serves webapp.html)
# =========================
flask_app = Flask(__name__)

@flask_app.get("/")
def index():
    try:
        with open("webapp.html", "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        html = "<h1>webapp.html not found</h1>"
    return Response(html, mimetype="text/html")


def run_flask():
    # Render прокидывает PORT
    port = int(os.getenv("PORT", "3000"))
    flask_app.run(host="0.0.0.0", port=port)


# =========================
# DB
# =========================
def normalize_digits(value) -> str:
    s = "" if value is None else str(value)
    s = s.strip().replace(" ", "")
    s = re.sub(r"\.0$", "", s)
    return s

def load_db() -> int:
    global df_cache
    if not os.path.exists(DB_FILE):
        df_cache = None
        return 0

    df = pd.read_excel(DB_FILE)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Не хватает колонок: " + ", ".join(missing))

    df["EAN"] = df["EAN"].apply(normalize_digits)
    df["SAP"] = df["SAP"].apply(normalize_digits)

    df_cache = df
    return len(df_cache)

def format_answer(row: pd.Series) -> str:
    return (
        f"✅ *{row['Название']}*\n\n"
        f"📍 Ряд: *{row['Ряд']}*\n"
        f"📦 Стеллаж: *{row['Стеллаж']}*\n"
        f"📐 Полка: *{row['Полка']}*\n"
        f"➡️ Позиция: *{row['Позиция']}*\n"
        f"👀 Фейсинг: *{row['Фейсинг']}*\n"
        f"📦 Упаковка: *{row['Упаковка']}*"
    )

def is_digits(s: str) -> bool:
    return bool(re.fullmatch(r"\d+", s))


# =========================
# KEYBOARD
# =========================
def get_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = []

    if PUBLIC_WEBAPP_URL:
        rows.append([KeyboardButton("📷 Сканировать", web_app=WebAppInfo(url=PUBLIC_WEBAPP_URL))])
    else:
        rows.append([KeyboardButton("📷 Сканировать (нет URL)")])

    if is_admin:
        rows.append([KeyboardButton("📥 Загрузить Excel")])

    rows.append([KeyboardButton("ℹ️ Помощь")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# =========================
# BOT HANDLERS
# =========================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    is_admin = (ADMIN_ID != 0 and user_id == ADMIN_ID)

    await update.message.reply_text(
        "Привет! Я PlanogramHelper ✅\n\n"
        "Отправь EAN (штрихкод) или SAP (цифры).\n"
        "Либо нажми «📷 Сканировать».\n\n"
        "Админ может обновить базу кнопкой «📥 Загрузить Excel» или /upload.",
        reply_markup=get_keyboard(is_admin),
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    is_admin = (ADMIN_ID != 0 and user_id == ADMIN_ID)

    await update.message.reply_text(
        "ℹ️ *Как пользоваться*\n\n"
        "• Вводишь/сканируешь EAN или SAP → я выдаю место.\n"
        "• Кнопка «📷 Сканировать» открывает камеру внутри Telegram.\n\n"
        "Админ:\n"
        "• «📥 Загрузить Excel» или /upload → отправляешь .xlsx как документ.\n\n"
        "Файл должен иметь колонки:\n"
        "EAN, SAP, Название, Ряд, Стеллаж, Полка, Позиция, Фейсинг, Упаковка",
        parse_mode="Markdown",
        reply_markup=get_keyboard(is_admin),
    )

async def cmd_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if ADMIN_ID == 0 or user_id != ADMIN_ID:
        await update.message.reply_text("❌ Команда доступна только админу.")
        return
    await update.message.reply_text("📥 Отправь Excel-файл (.xlsx) одним документом.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else 0
    if ADMIN_ID == 0 or user_id != ADMIN_ID:
        await update.message.reply_text("❌ Загружать базу может только админ.")
        return

    doc = update.message.document
    if not doc or not doc.file_name or not doc.file_name.lower().endswith(".xlsx"):
        await update.message.reply_text("❌ Нужен файл .xlsx")
        return

    file = await context.bot.get_file(doc.file_id)
    await file.download_to_drive(DB_FILE)

    try:
        n = load_db()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка в базе: {e}")
        return

    await update.message.reply_text(f"✅ База обновлена! ({n} строк)")

async def search_and_reply(update: Update, query: str):
    global df_cache
    if df_cache is None:
        await update.message.reply_text("⚠️ База ещё не загружена. Админ должен загрузить Excel через /upload.")
        return

    q = query.replace(" ", "").strip()
    if not is_digits(q):
        await update.message.reply_text("❌ Нужны только цифры (EAN или SAP).")
        return

    # 8-14 цифр = EAN, иначе SAP
    if 8 <= len(q) <= 14:
        found = df_cache[df_cache["EAN"] == q]
    else:
        found = df_cache[df_cache["SAP"] == q]

    if found.empty:
        await update.message.reply_text("❌ Не найдено. Проверь EAN/SAP.")
        return

    if len(found) > 5:
        await update.message.reply_text(f"⚠️ Найдено {len(found)} совпадений. Показываю первые 5:")
        found = found.head(5)

    for _, row in found.iterrows():
        await update.message.reply_text(format_answer(row), parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.text is None:
        return
    text = update.message.text.strip()

    if text == "ℹ️ Помощь":
        await cmd_help(update, context)
        return
    if text == "📥 Загрузить Excel":
        await cmd_upload(update, context)
        return

    await search_and_reply(update, text)

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.message.web_app_data.data if update.message and update.message.web_app_data else ""
    if not data:
        return
    await search_and_reply(update, data)


def run_bot():
    if not BOT_TOKEN:
        raise RuntimeError("Не найден BOT_TOKEN. Добавь его в Render → Environment.")

    # если база уже есть
    try:
        load_db()
    except Exception:
        pass

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("upload", cmd_upload))

    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Bot started")
    app.run_polling()


if __name__ == "__main__":
    # Flask в отдельном потоке
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    # Бот в главном потоке
    run_bot()
