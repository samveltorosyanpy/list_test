#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
list.am sniper — следит за обычными объявлениями (от людей) и сообщает о новых.

Берёт ТОЛЬКО объявления после заголовка "Սովորական հայտարարություններ"
(обычные объявления / люди) и игнорирует рекламный блок
"Թոփ հայտարարություններ" (топ/реклама), который идёт выше.

Зависимости:
    pip install requests beautifulsoup4

Запуск:
    python3 listam_sniper.py                 # цикл: проверка каждые 3 минуты
    python3 listam_sniper.py --once          # одна проверка и выход
    python3 listam_sniper.py --interval 60   # цикл с другим периодом (сек)

Первый запуск создаёт базовый список и НЕ показывает ничего как «новое».
Со второго запуска печатает только новые объявления.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ─────────────────────────── НАСТРОЙКИ ───────────────────────────
URL = "https://www.list.am/category/62?n=1%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%2C13%2C11%2C12&sname=&s=&cmtype=0&crc=&price1=&price2=&cnd="   # раздел "Продажа" недвижимости
# Чистый URL без ?n=... — вариант с n= часто отдаёт пустой ответ.

# Маркер, после которого идут обычные объявления (от людей).
MARKER = "Սովորական հայտարարություններ"

# Файл состояния (рядом со скриптом).
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "listam_seen_ids.json")

POLL_SECONDS = 180         # период проверки (180 = 3 минуты)
MAX_REMEMBERED = 5000      # сколько ID хранить в памяти максимум

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept-Language": "ru,hy;q=0.9,en;q=0.8",
}
# ──────────────────────────────────────────────────────────────────


def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def slice_after_marker(html: str) -> str:
    """Вернуть часть HTML после заголовка обычных объявлений.

    Так рекламный блок 'Թոփ հայտարարություններ' (он идёт раньше) отсекается.
    Если маркер не найден — возвращаем весь html (на всякий случай).
    """
    idx = html.find(MARKER)
    if idx == -1:
        return html
    return html[idx:]


def parse_listings(html: str) -> dict:
    """Распарсить объявления из (уже обрезанного) HTML.

    Возвращает dict: id -> {price, info, url}.
    """
    soup = BeautifulSoup(html, "html.parser")
    items = {}
    for a in soup.find_all("a", href=re.compile(r"/item/\d+")):
        m = re.search(r"/item/(\d+)", a.get("href", ""))
        if not m:
            continue
        item_id = m.group(1)
        if item_id in items:
            continue

        price_el = a.select_one(".p")
        info_el = a.select_one(".at")
        loc_el = a.select_one(".l")

        price = price_el.get_text(strip=True) if price_el else ""
        info = info_el.get_text(strip=True) if info_el else ""
        loc = loc_el.get_text(strip=True) if loc_el else ""
        # запасной вариант, если структура другая — берём весь текст ссылки
        if not (price or info):
            info = a.get_text(" ", strip=True)[:160]

        desc = ", ".join(p for p in (loc, info) if p)
        items[item_id] = {
            "price": price,
            "info": desc,
            "url": f"https://www.list.am/item/{item_id}",
        }
    return items


def load_state() -> set:
    if not os.path.exists(STATE_FILE):
        return None  # None = первый запуск
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("seen_ids", []))
    except (json.JSONDecodeError, OSError):
        return None


def save_state(seen_ids: set):
    ids = list(seen_ids)
    if len(ids) > MAX_REMEMBERED:
        # оставляем последние (самые большие ID — самые новые)
        ids = sorted(ids, key=lambda x: int(x))[-MAX_REMEMBERED:]
    data = {
        "url": URL,
        "updated": datetime.now().isoformat(timespec="seconds"),
        "seen_ids": ids,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def notify(new_items: dict):
    """Печать новых объявлений. Здесь же можно добавить Telegram/звук и т.п."""
    print(f"\n🔔 НОВЫХ ОБЪЯВЛЕНИЙ: {len(new_items)}  "
          f"({datetime.now():%Y-%m-%d %H:%M:%S})")
    print("─" * 60)
    # новые сверху (больший ID = новее)
    for item_id in sorted(new_items, key=lambda x: int(x), reverse=True):
        it = new_items[item_id]
        line = " | ".join(p for p in (it["price"], it["info"]) if p)
        print(f"  {line}")
        print(f"  {it['url']}")
        print()


def check_once() -> int:
    html = fetch_html(URL)
    html = slice_after_marker(html)
    current = parse_listings(html)

    if not current:
        print("⚠️  Объявления не найдены — возможно, изменилась структура "
              "страницы или маркер.", file=sys.stderr)
        return 0

    seen = load_state()

    if seen is None:
        # первый запуск — создаём базу, ничего не «снайпим»
        save_state(set(current.keys()))
        print(f"✅ Базовый список создан: {len(current)} объявлений. "
              f"Со следующей проверки буду показывать только новые.")
        return 0

    new_ids = [i for i in current if i not in seen]
    new_items = {i: current[i] for i in new_ids}

    # обновляем состояние (старые + текущие)
    save_state(seen | set(current.keys()))

    if new_items:
        notify(new_items)
    else:
        print(f"Новых объявлений нет ({datetime.now():%H:%M:%S}).")
    return len(new_items)


def main():
    ap = argparse.ArgumentParser(description="list.am sniper (обычные объявления)")
    ap.add_argument("--once", action="store_true",
                    help="выполнить ОДНУ проверку и выйти (без цикла)")
    ap.add_argument("--interval", type=int, default=POLL_SECONDS,
                    help=f"период в секундах для цикла (по умолчанию {POLL_SECONDS} = 3 мин)")
    args = ap.parse_args()

    if args.once:
        check_once()
        return

    # По умолчанию — бесконечный цикл с проверкой каждые args.interval секунд.
    print(f"▶️  Слежу за {URL}\n   проверка каждые {args.interval} сек. "
          f"({args.interval // 60} мин). Ctrl+C для выхода.")
    while True:
        try:
            check_once()
        except requests.RequestException as e:
            print(f"⚠️  Ошибка загрузки: {e}", file=sys.stderr)
        except Exception as e:  # noqa
            print(f"⚠️  Ошибка: {e}", file=sys.stderr)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()