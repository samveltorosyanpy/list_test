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
import json
from urllib.parse import urlencode


# Функция для сборки правильного URL под list.am
def build_listam_url(filters: dict) -> str:
    category_id = filters.get("category_id", "62")  # По умолчанию Продажа (62)
    base_url = f"https://www.list.am/category/{category_id}"
    print(filters)
    # Собираем query-параметры (GET)
    query_params = {}

    # 1. Локации (Районы)
    # Если выбраны районы, склеиваем их через запятую (например: 1,2,3)
    # Если массив пустой, параметр 'n' вообще не передаем (ищет по всей Армении)
    regions_ids = filters.get("regions_ids", [])
    if regions_ids:
        query_params["n"] = ",".join(map(str, regions_ids))

    # 2. Валюта
    # crc=0 (AMD), crc=1 (USD), crc=2 (EUR), crc=3 (RUB)
    if filters.get("currency_id") is not None:
        query_params["crc"] = filters.get("currency_id")

    # 3. Минимальная цена
    if filters.get("min_price") and int(filters.get("min_price")) > 0:
        query_params["price1"] = filters.get("min_price")

    # 4. Максимальная цена
    if filters.get("max_price") and str(filters.get("max_price")).isdigit():
        query_params["price2"] = filters.get("max_price")

    # 5. Состояние здания (cnd=4 или cnd=5)
    if filters.get("cnd_id") is not None:
        query_params["cnd"] = filters.get("cnd_id")

    # 6. Тип продавца (user=1 или user=2)
    if filters.get("user_id") is not None:
        query_params["user"] = filters.get("user_id")

    # Склеиваем параметры в строку вида ?n=1,2&crc=1...
    if query_params:
        final_url = f"{base_url}?{urlencode(query_params)}"
    else:
        final_url = base_url

    return final_url


# Твой обработчик входящих данных из WebApp (aiogram/long polling)
# Если используешь кастомный long-polling (как в твоем базовом файле),
# то разбор message["web_app_data"]["data"] будет выглядеть так:
def process_filters_json(raw_data: str) -> str:
    try:
        filters = json.loads(raw_data)
        # Генерируем ссылку для парсера
        generated_url = build_listam_url(filters)

        # Формируем красивый отчет для пользователя
        regions_list = "\n• " + "\n• ".join(filters.get('regions_names', ['Не выбраны']))

        report_text = (
            f"🎯 **Фильтры успешно применены!**\n\n"
            f"🗂 **Раздел:** {filters.get('category_text')}\n"
            f"💰 **Валюта:** {filters.get('currency_text')}\n"
            f"💵 **Цена:** от `{filters.get('min_price')}` до `{filters.get('max_price')}`\n"
            f"🏗 **Состояние:** {filters.get('cnd_text')}\n"
            f"👤 **Продавец:** {filters.get('user_text')}\n"
            f"📍 **Районы:** {regions_list}\n\n"
            f"🔗 **Сгенерированный URL для парсинга:**\n`{generated_url}`"
        )
        return report_text

    except Exception as e:
        return f"❌ Ошибка генерации URL: {e}", ""

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
        report_text = process_filters_json(raw_data)

        await message.answer(report_text, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ Ошибка обработки данных: {e}")


async def main():
    print("🚀 Бот на aiogram успешно запущен в режиме Long Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())