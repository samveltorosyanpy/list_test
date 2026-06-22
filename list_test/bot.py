# ─────────────────────────── НАСТРОЙКИ ───────────────────────────
import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

# Токен берем из переменных окружения или вставляем напрямую
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8028071328:AAH3M-4DlI5IchPZZbpYKWUxYIvcrfUcFi8")

# СЮДА ВСТАВЬ СВОЮ ССЫЛКУ НА GITHUB PAGES
WEBAPP_URL = "https://samveltorosyanpy.github.io/list_test/index.html"

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Хэндлер на команду /start создает кнопку для открытия WebApp"""

    # Создаем кнопку, которая развернет наш сайт внутри Telegram
    webapp_button = KeyboardButton(
        text="⚙️ Открыть фильтры",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[webapp_button]],
        resize_keyboard=True
    )

    await message.answer(
        text="Привет! Нажми на кнопку ниже, чтобы настроить фильтры для недвижимости.",
        reply_markup=keyboard
    )


@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    """Хэндлер ловит данные, отправленные из WebApp через tg.sendData"""
    raw_data = message.web_app_data.data

    try:
        # Распаковываем JSON, который пришел из JavaScript
        filters = json.loads(raw_data)

        # Красиво форматируем ответ для брокера (Эхо фильтров)
        response_text = (
            "📥 **Получены новые настройки фильтров:**\n\n"
            f"💵 **Валюта:** {filters.get('currency')}\n"
            f"💰 **Макс. цена:** {filters.get('max_price')}\n"
            f"📍 **Выбранные районы:** {', '.join(filters.get('regions_names'))}\n\n"
            "_Данные успешно приняты ботом! На следующем этапе мы свяжем их с генератором URL и базой данных._"
        )

        await message.answer(response_text, parse_mode="Markdown")

    except Exception as e:
        await message.answer(f"❌ Ошибка обработки данных: {e}")


async def main():
    print("🚀 Бот на aiogram успешно запущен в режиме Long Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())