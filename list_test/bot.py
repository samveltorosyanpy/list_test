#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram-бот (long polling) для слежки за обычными объявлениями на list.am.

Бот делает две вещи одновременно:
  1) Long polling Telegram (getUpdates) — слушает команды от тебя.
  2) Фоновый цикл — каждые 3 минуты парсит list.am и шлёт НОВЫЕ
     обычные объявления (после "Սովորական հայտարարություններ") всем
     подписчикам.

Команды в чате с ботом:
  /start  — подписаться (бот начнёт слать новые объявления)
  /stop   — отписаться
  /status — статистика (подписчики, сколько ID в базе, последняя проверка)
  /check  — проверить прямо сейчас

─────────────────────────── НАСТРОЙКА ───────────────────────────
1. Установи зависимости:
       pip install requests beautifulsoup4
2. Создай бота у @BotFather в Telegram → получишь токен вида
       123456789:AAEhBP...
3. Передай токен боту одним из способов:
       export TELEGRAM_BOT_TOKEN="123456789:AAE..."   (macOS/Linux)
   или впиши его ниже в TOKEN.
4. Запусти:
       python3 listam_telegram_bot.py
5. В Telegram напиши своему боту  /start  — и всё.

Файл listam_sniper.py должен лежать рядом (из него берётся парсинг).
"""

import os
import sys
import json
import time
import threading
from datetime import datetime

import requests

# Переиспользуем логику парсинга из listam_sniper.py
from sniper_test import (
    URL, fetch_html, slice_after_marker, parse_listings,
    load_state, save_state,
)

# ─────────────────────────── НАСТРОЙКИ ───────────────────────────
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8028071328:AAH3M-4DlI5IchPZZbpYKWUxYIvcrfUcFi8")
CHECK_INTERVAL = 180          # период проверки сайта, сек (180 = 3 мин)
MAX_PER_CYCLE = 15            # максимум сообщений за одну проверку (анти-флуд)

_HERE = os.path.dirname(os.path.abspath(__file__))
SUBS_FILE = os.path.join(_HERE, "telegram_subscribers.json")
API = f"https://api.telegram.org/bot{TOKEN}"
# ──────────────────────────────────────────────────────────────────

_last_check = "ещё не было"
_lock = threading.Lock()


# ─────────────────────── подписчики ───────────────────────
def load_subs() -> set:
    if not os.path.exists(SUBS_FILE):
        return set()
    try:
        with open(SUBS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f).get("chat_ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_subs(subs: set):
    with open(SUBS_FILE, "w", encoding="utf-8") as f:
        json.dump({"chat_ids": sorted(subs)}, f, ensure_ascii=False, indent=2)


# ─────────────────────── Telegram API ───────────────────────
def tg(method: str, **params):
    try:
        r = requests.post(f"{API}/{method}", data=params, timeout=40)
        return r.json()
    except requests.RequestException as e:
        print(f"⚠️  Telegram {method}: {e}", file=sys.stderr)
        return {}


def send_message(chat_id, text: str):
    # без parse_mode — обычный текст, ссылки Telegram превратит в превью сам
    tg("sendMessage", chat_id=chat_id, text=text,
       disable_web_page_preview=False)


def broadcast(text: str):
    for chat_id in load_subs():
        send_message(chat_id, text)
        time.sleep(0.1)


def format_item(it: dict) -> str:
    head = " | ".join(p for p in (it["price"], it["info"]) if p)
    return f"🏠 {head}\n{it['url']}"


# ─────────────────────── проверка сайта ───────────────────────
def do_check(announce_to=None) -> int:
    """Проверить сайт. Вернуть число новых. Новые рассылаются подписчикам.

    announce_to: если задан chat_id — отправить туда краткий итог (для /check).
    """
    global _last_check
    html = slice_after_marker(fetch_html(URL))
    current = parse_listings(html)
    _last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not current:
        if announce_to:
            send_message(announce_to, "⚠️ Объявления не найдены (структура страницы?).")
        return 0

    with _lock:
        seen = load_state()
        if seen is None:
            save_state(set(current.keys()))
            if announce_to:
                send_message(announce_to,
                             f"✅ Базовый список создан: {len(current)}. "
                             f"Дальше буду слать только новые.")
            return 0
        new_ids = [i for i in current if i not in seen]
        save_state(seen | set(current.keys()))

    new_items = [current[i] for i in sorted(new_ids, key=int, reverse=True)]

    if new_items:
        shown = new_items[:MAX_PER_CYCLE]
        broadcast(f"🔔 Новых объявлений: {len(new_items)}")
        for it in shown:
            broadcast(format_item(it))
        if len(new_items) > MAX_PER_CYCLE:
            broadcast(f"…и ещё {len(new_items) - MAX_PER_CYCLE}. "
                      f"Смотри на list.am: {URL}")
    elif announce_to:
        send_message(announce_to, "Новых объявлений нет.")

    return len(new_items)


def site_loop():
    print(f"🔁 Фоновая проверка каждые {CHECK_INTERVAL} сек.")
    while True:
        try:
            n = do_check()
            print(f"[{datetime.now():%H:%M:%S}] проверка — новых: {n}")
        except Exception as e:  # noqa
            print(f"⚠️  Ошибка проверки: {e}", file=sys.stderr)
        time.sleep(CHECK_INTERVAL)


# ─────────────────────── обработка команд ───────────────────────
# ─────────────────────── Изменения в обработке команд ───────────────────────

def handle_command(text: str, chat_id):
    cmd = text.strip().split()[0].lower().split("@")[0]
    if cmd == "/start":
        subs = load_subs()
        subs.add(chat_id)
        save_subs(subs)

        # Ссылка на твой развернутый index.html (замени на свою!)
        WEBAPP_URL = "https://your-username.github.io/listam-webapp/"

        # Создаем кнопку для открытия WebApp
        keyboard = {
            "keyboard": [[
                {
                    "text": "⚙️ Настроить валюту (WebApp)",
                    "web_app": {"url": WEBAPP_URL}
                }
            ]],
            "resize_keyboard": True
        }

        # Отправляем сообщение вместе с кнопкой WebApp
        try:
            requests.post(f"{API}/sendMessage", data={
                "chat_id": chat_id,
                "text": (f"✅ Подписка оформлена. Проверка каждые {CHECK_INTERVAL // 60} мин.\n"
                         "Нажми на кнопку ниже, чтобы выбрать валюту!"),
                "reply_markup": json.dumps(keyboard)
            }, timeout=40)
        except Exception as e:
            print(f"Ошибка отправки клавиатуры: {e}")

    # ... твои остальные команды (/stop, /status) остаются без изменений


def updates_loop():
    offset = None
    print("👂 Слушаю команды Telegram (long polling)…")
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(f"{API}/getUpdates", params=params, timeout=40).json()
        except requests.RequestException as e:
            print(f"⚠️  getUpdates: {e}", file=sys.stderr)
            time.sleep(3)
            continue

        if not resp.get("ok"):
            print(f"⚠️  Telegram ответил: {resp}", file=sys.stderr)
            time.sleep(3)
            continue

        for upd in resp.get("result", []):
            offset = upd["update_id"] + 1
            msg = upd.get("message") or upd.get("channel_post")
            if not msg:
                continue
            chat_id = msg["chat"]["id"]

            # ПРОВЕРКА: Пришли ли данные из WebApp?
            if "web_app_data" in msg:
                raw_json = msg["web_app_data"]["data"]  # Это то, что отправил tg.sendData
                try:
                    web_data = json.loads(raw_json)
                    new_url = web_data.get("url")
                    currency = web_data.get("currency")

                    # ⚠️ ВАЖНО: Перезаписываем глобальную переменную URL в модуле снайпера!
                    import sniper_test
                    sniper_test.URL = new_url

                    send_message(chat_id, f"⚙️ Настройки успешно изменены!\n"
                                          f"Выбранная валюта: *{currency}*\n"
                                          f"Новый URL для парсера сохранен.")

                    # Опционально: сразу запускаем проверку по новому URL
                    send_message(chat_id, "🔎 Запускаю внеочередную проверку...")
                    do_check(announce_to=chat_id)

                except Exception as e:
                    send_message(chat_id, f"⚠️ Ошибка обработки настроек: {e}")
                continue  # Переходим к следующему апдейту

            # Если это обычный текст/команда
            text = msg.get("text", "")
            if text.startswith("/"):
                handle_command(text, chat_id)


def main():
    if not TOKEN or TOKEN == "PASTE_YOUR_TOKEN_HERE":
        sys.exit("❌ Не задан токен. Установи TELEGRAM_BOT_TOKEN или впиши TOKEN в файл.\n"
                 "   Токен получи у @BotFather в Telegram.")
    # проверим токен
    me = tg("getMe")
    if not me.get("ok"):
        sys.exit(f"❌ Токен не принят Telegram: {me}")
    print(f"🤖 Бот @{me['result'].get('username')} запущен.")

    threading.Thread(target=site_loop, daemon=True).start()
    try:
        updates_loop()
    except KeyboardInterrupt:
        print("\n👋 Остановлено.")


if __name__ == "__main__":
    main()