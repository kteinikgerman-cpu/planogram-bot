import telebot
from telebot import types
import pandas as pd
import os

# Токен из переменных окружения (безопасность!)
BOT_TOKEN = "7564138089:AAFZm0WjZ_EObBCUb8KXxCmKKxk_YpZD5VM"
EXCEL_FILE = 'base.xlsx'  # Файл будет загружен на GitHub
WEB_APP_URL = 'https://kteinikgerman-cpu.github.io/planogram-bot/webapp.html'

bot = telebot.TeleBot(BOT_TOKEN)

def load_products():
    try:
        df = pd.read_excel(EXCEL_FILE)
        print(f"✅ Загружено {len(df)} товаров")
        return df
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

products_df = load_products()

def search_product(code):
    if products_df is None:
        return None
    try:
        code_num = int(code)
    except:
        return None
    result = products_df[products_df['EAN'] == code_num]
    if result.empty:
        result = products_df[products_df['SAP'] == code_num]
    if not result.empty:
        return result.iloc[0]
    return None

def format_product_info(product):
    message = f"📦 <b>{product['Название']}</b>\n\n"
    message += f"🔢 <b>Коды:</b>\n"
    message += f"   • SAP: <code>{product['SAP']}</code>\n"
    message += f"   • EAN: <code>{product['EAN']}</code>\n\n"
    message += f"📍 <b>МЕСТОПОЛОЖЕНИЕ:</b>\n"
    message += f"   🏪 Ряд: <b>{product['Ряд']}</b>\n"
    message += f"   📊 Стеллаж: <b>{product['Стеллаж']}</b>\n"
    message += f"   📐 Полка: <b>{product['Полка']}</b>\n"
    message += f"   📌 Позиция: <b>{product['Позиция']}</b>\n\n"
    message += f"📦 <b>Упаковка:</b>\n"
    message += f"   • Фейсинг: <b>{product['Фейсинг']}</b>\n"
    message += f"   • Тип: <b>{product['Упаковка']}</b>"
    return message

def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    scan_button = types.KeyboardButton(text="📸 Сканировать", web_app=types.WebAppInfo(url=WEB_APP_URL))
    keyboard.add(scan_button)
    keyboard.add("📊 Статистика", "ℹ️ Помощь")
    return keyboard

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = "👋 Добро пожаловать!\n\n📸 Нажмите кнопку сканера\n⌨️ Или отправьте SAP/EAN код"
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=get_main_keyboard())

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if products_df is not None:
        stats_text = f"📊 Товаров: {len(products_df)}\n🏪 Рядов: {products_df['Ряд'].nunique()}"
        bot.reply_to(message, stats_text, parse_mode='HTML')
    else:
        bot.reply_to(message, "Ошибка загрузки данных")

@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    code = message.web_app_data.data
    print(f"📸 Получен код: {code}")
    product = search_product(code)
    if product is not None:
        info = format_product_info(product)
        bot.send_message(message.chat.id, info, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, f"❌ Товар {code} не найден", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats_button(message):
    show_stats(message)

@bot.message_handler(func=lambda m: m.text == "ℹ️ Помощь")
def help_button(message):
    send_welcome(message)

@bot.message_handler(func=lambda message: True)
def search_handler(message):
    code = message.text.strip()
    if not code.isdigit():
        bot.reply_to(message, "⚠️ Введите только цифры или используйте сканер")
        return
    product = search_product(code)
    if product is not None:
        info = format_product_info(product)
        bot.reply_to(message, info, parse_mode='HTML')
    else:
        bot.reply_to(message, f"❌ Товар {code} не найден")

if __name__ == '__main__':
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН НА RENDER!")
    print("=" * 50)
    if products_df is not None:
        print(f"📦 Товаров в базе: {len(products_df)}")
        print("✅ Бот готов к работе!")
    else:
        print("❌ ОШИБКА загрузки данных!")
    print("=" * 50)
    
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
