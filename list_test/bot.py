#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import asyncio
from urllib.parse import urlencode

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Импортируем наш облегченный парсер из соседнего файла parser.py
from list_test.parsers.parser import parse_listam

# ─────────────────────────── НАСТРОЙКИ ───────────────────────────
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8028071328:AAH3M-4DlI5IchPZZbpYKWUxYIvcrfUcFi8")

SETTINGS_FILE = "user_settings.json"
SEEN_FILE = "listam_seen_ids.json"
POLL_SECONDS = 30  # Интервал проверки сайта — 30 секунд (режим тестов)

DEFAULT_URL = "https://www.list.am/category/62"

# Адрес WebApp с фильтрами (GitHub Pages со статичным index.html).
# ВАЖНО: должен быть HTTPS. Можно переопределить через переменную окружения.
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://samveltorosyanpy.github.io/list_test/")

# Инициализируем бот и диспетчер
bot = Bot(token=TOKEN, default_properties=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()


# ─────────────────── СИНХРОННЫЕ ХЕЛПЕРЫ ДЛЯ ФАЙЛОВ ───────────────────
# Чтобы не усложнять код, чтение/запись небольших JSON сделаем через обычный open,
# но будем вызывать аккуратно, так как объемы данных тут крошечные.

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"url": DEFAULT_URL, "subscribers": []}


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)


MAX_REMEMBERED = 5000  # сколько id держим в кэше максимум (чтобы не рос бесконечно)


def load_seen() -> set:
    """Читает множество уже виденных id объявлений."""
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {int(x) for x in data.get("seen_ids", [])}
            if isinstance(data, list):  # совместимость со старым форматом
                return {int(x) for x in data}
        except Exception:
            pass
    return set()


def save_seen(seen_ids: set):
    # Храним только последние (наибольшие) id, чтобы файл не разрастался.
    ids = sorted(seen_ids)[-MAX_REMEMBERED:]
    with open(SEEN_FILE, "w") as f:
        json.dump({"seen_ids": ids}, f)


# Общий кэш виденных id. Один объект на процесс: его мутируют (in-place)
# и фоновый цикл, и хендлеры, поэтому все видят одни и те же данные.
# «Новое объявление» = id, которого нет в seen.
seen = load_seen()


def remember(ids):
    """Добавляет id в кэш seen, подрезает его до лимита и сохраняет на диск."""
    seen.update(ids)
    if len(seen) > MAX_REMEMBERED:
        keep = set(sorted(seen)[-MAX_REMEMBERED:])
        seen.clear()
        seen.update(keep)
    save_seen(seen)


# ───────────────────────── КЛАВИАТУРА WEBAPP ─────────────────────────

def filters_keyboard() -> types.ReplyKeyboardMarkup:
    """
    Reply-клавиатура с кнопкой запуска WebApp.
    ВАЖНО: WebApp надо открывать именно из KeyboardButton(web_app=...),
    только тогда tg.sendData(...) из index.html вернётся в хендлер F.web_app_data.
    """
    return types.ReplyKeyboardMarkup(
        keyboard=[[
            types.KeyboardButton(
                text="🔧 Открыть фильтры",
                web_app=types.WebAppInfo(url=WEBAPP_URL),
            )
        ]],
        resize_keyboard=True,
    )


# ─────────────────────── СБОРКА URL ИЗ WEBAPP ───────────────────────

def build_listam_url(filters: dict) -> str:
    category_id = filters.get("category_id", "62")
    base_url = f"https://www.list.am/category/{category_id}"
    query_params = {}

    if filters.get("regions_ids"):
        query_params["n"] = ",".join(map(str, filters["regions_ids"]))
    if filters.get("currency_id") is not None:
        query_params["crc"] = filters["currency_id"]
    if filters.get("min_price") and int(filters["min_price"]) > 0:
        query_params["price1"] = filters["min_price"]
    if filters.get("max_price") and str(filters["max_price"]).isdigit():
        query_params["price2"] = filters["max_price"]
    if filters.get("cnd_id") is not None:
        query_params["cnd"] = filters["cnd_id"]
    if filters.get("user_id") is not None:
        query_params["user"] = filters["user_id"]

    return f"{base_url}?{urlencode(query_params)}" if query_params else base_url


# ────────────────── АСИНХРОННЫЙ ФОНОВЫЙ ЦИКЛ (LOOP) ──────────────────

async def background_sniper_loop():
    print("▶️ Асинхронный фоновый цикл снайпера запущен.")

    while True:
        try:
            settings = load_settings()
            current_url = settings.get("url", DEFAULT_URL)
            subscribers = settings.get("subscribers", [])

            if subscribers:
                print(f"🔍 [Проверка] Сканирую: {current_url}")

                # Поскольку parse_listam внутри использует синхронный requests,
                # мы запускаем его в отдельном потоке執行, чтобы он не вешал асинхронный Event Loop бота.
                loop = asyncio.get_running_loop()
                current_items = await loop.run_in_executor(None, parse_listam, current_url)

                if current_items:
                    if not seen:
                        # Кэша ещё нет — делаем базовый снимок и НИЧЕГО не рассылаем.
                        remember(current_items.keys())
                        print(f"📌 Базовый снимок: запомнено {len(current_items)} объявлений.")
                    else:
                        # Новое = любой id, которого нет в seen (а не «больше максимума»).
                        new_ids = [i for i in current_items if i not in seen]
                        if new_ids:
                            print(f"🔥 Найдено новых постов: {len(new_ids)}")
                            # Новые сверху: больший id — более свежее объявление.
                            for i in sorted(new_ids, reverse=True):
                                post_url = current_items[i]
                                for chat_id in subscribers:
                                    try:
                                        await bot.send_message(chat_id=chat_id, text=post_url)
                                    except Exception as send_err:
                                        print(f"⚠️ Ошибка отправки пользователю {chat_id}: {send_err}")
                            # Запоминаем разосланные id, чтобы не слать повторно.
                            remember(new_ids)
            else:
                print("💤 Нет активных подписчиков. Пропускаю круг.")

        except Exception as e:
            print(f"⚠️ Ошибка в фоновом цикле снайпера: {e}", file=sys.stderr)

        # Асинхронный сон (POLL_SECONDS не блокирует процессор)
        await asyncio.sleep(POLL_SECONDS)


# ────────────────────── ОБРАБОТКА ХЕНДЛЕРОВ AIOGRAM ──────────────────────

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    chat_id = message.chat.id
    settings = load_settings()

    if chat_id not in settings["subscribers"]:
        settings["subscribers"].append(chat_id)
        save_settings(settings)

    await message.answer(
        "👋 Привет! Я начал слежку за объявлениями на list.am.\n"
        "Нажми «🔧 Открыть фильтры», чтобы настроить нужные параметры!",
        reply_markup=filters_keyboard(),
    )

    # При подписке запоминаем ВСЮ текущую выдачу как базовый снимок и ничего
    # не рассылаем. Дальше фоновый цикл будет слать только то, чего нет в seen.
    current_url = settings.get("url", DEFAULT_URL)
    loop = asyncio.get_running_loop()
    current_items = await loop.run_in_executor(None, parse_listam, current_url)

    if current_items:
        remember(current_items.keys())
        await message.answer(
            f"🔍 Слежка запущена. Запомнил {len(current_items)} текущих объявлений — "
            "пришлю ссылку, как только появится новое."
        )
    else:
        await message.answer(
            "⚠️ Сейчас не удалось получить выдачу, но слежка активна — "
            "проверю снова автоматически через несколько минут."
        )


@dp.message(Command("filters"))
async def cmd_filters(message: types.Message):
    # Повторно показываем кнопку WebApp, если клавиатура пропала.
    await message.answer("🔧 Открой фильтры:", reply_markup=filters_keyboard())


@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    chat_id = message.chat.id
    settings = load_settings()

    if chat_id in settings["subscribers"]:
        settings["subscribers"].remove(chat_id)
        save_settings(settings)

    await message.answer("🛑 Слежка остановлена. Вы исключены из рассылки.")


# Хендлер для приема данных из WebApp (клик на кнопку отправки данных внутри WebApp)
@dp.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    chat_id = message.chat.id
    raw_json = message.web_app_data.data
    settings = load_settings()

    try:
        filters = json.loads(raw_json)
        new_url = build_listam_url(filters)

        # Обновляем URL для слежки
        settings["url"] = new_url
        if chat_id not in settings["subscribers"]:
            settings["subscribers"].append(chat_id)
        save_settings(settings)

        # Красивый отчет о примененных фильтрах
        regions = "\n• " + "\n• ".join(filters.get('regions_names', ['Не выбраны']))
        report = (
            f"🚀 **Фильтры успешно применены!**\n\n"
            f"🗂 Раздел: {filters.get('category_text')}\n"
            f"🔄 Лента: {filters.get('post_type_text')}\n"
            f"💰 Валюта: {filters.get('currency_text')}\n"
            f"💵 Цена: от {filters.get('min_price')} до {filters.get('max_price')}\n"
            f"🏗 Состояние: {filters.get('cnd_text')}\n"
            f"👤 Продавец: {filters.get('user_text')}\n"
            f"📍 Районы: {regions}\n\n"
            f"📋 *Ссылка слежки:* `{new_url}`"
        )
        await message.answer(report, reply_markup=filters_keyboard())

        # Лента сменилась — пере-засеваем кэш под новый URL, чтобы не вывалить
        # сразу всю текущую выдачу нового фильтра как «новую».
        loop = asyncio.get_running_loop()
        current_items = await loop.run_in_executor(None, parse_listam, new_url)
        seen.clear()
        if current_items:
            remember(current_items.keys())
        else:
            save_seen(seen)

    except Exception as e:
        await message.answer(f"❌ Ошибка применения фильтров: {e}")


# ────────────────────────────────── ЗАПУСК ──────────────────────────────────

async def main():
    if not TOKEN or TOKEN == "PASTE_YOUR_TOKEN_HERE":
        sys.exit("❌ Ошибка: Укажите корректный TELEGRAM_BOT_TOKEN!")

    # Запускаем фоновый цикл снайпера как асинправную задачу asyncio task
    asyncio.create_task(background_sniper_loop())

    print("🤖 Бот на aiogram 3 запущен и готов к работе...")
    # Запускаем поллинг бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Бот остановлен.")