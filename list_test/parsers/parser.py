#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "hy-AM,hy;q=0.9,ru-RU;q=0.8,ru;q=0.7,en-US;q=0.6,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

from curl_cffi import requests as cffi_requests

# Заголовок «Обычные объявления» (от людей). Над ним идут VIP/ТОП-блоки.
MARKER = "Սովորական հայտարարություններ"

# Регулярка ссылки на объявление: /item/<цифры>
ITEM_HREF = re.compile(r"^/item/\d+")


def _extract_items(scope) -> dict:
    """Собирает {id: url} из всех ссылок /item/ внутри переданного куска DOM."""
    items = {}
    for a in scope.find_all("a", href=ITEM_HREF):
        match = re.search(r"/item/(\d+)", a["href"])
        if not match:
            continue
        item_id = int(match.group(1))
        items[item_id] = f"https://www.list.am{a['href']}"
    return items


def parse_listam(url: str) -> dict:
    """
    Парсит URL-адрес list.am и вытаскивает ссылки ТОЛЬКО на обычные объявления.

    Основная стратегия: режем HTML по армянскому маркеру «обычных объявлений»
    (Սովորական հայտարարություններ) — всё, что выше (VIP/ТОП), отсекается.
    Запасная стратегия (если маркера нет): берём последний НЕ пустой div.gl.
    """
    try:
        response = cffi_requests.get(url, headers=HEADERS, impersonate="chrome120", timeout=15)
    except Exception as e:
        print(f"❌ [Parser Error] Ошибка запроса к сайту: {e}", file=sys.stderr)
        return {}

    html = response.text

    # ── Стратегия 1: срез по маркеру обычных объявлений ──
    idx = html.find(MARKER)
    if idx != -1:
        scope = BeautifulSoup(html[idx:], "html.parser")
        items = _extract_items(scope)
        if items:
            return items

    # ── Стратегия 2 (fallback): последний НЕ пустой контейнер div.gl ──
    soup = BeautifulSoup(html, "html.parser")
    gl_with_items = [c for c in soup.find_all("div", class_="gl") if c.find("a", href=ITEM_HREF)]
    if not gl_with_items:
        print("⚠️ [Parser Warning] Обычные объявления не найдены "
              "(нет маркера и нет непустых div.gl).", file=sys.stderr)
        return {}

    return _extract_items(gl_with_items[-1])

def run_test():
    # Тестовый URL (Продажа недвижимости, валюта: AMD)
    test_url = "https://www.list.am/category/62?crc=0"

    print("📡 Запуск изолированного теста парсера...")
    print(f"🔗 URL: {test_url}")
    print("-" * 50)

    # Достаём ссылки из всех блоков div.gl
    result = parse_listam(test_url)

    if not result:
        print("❌ Ничего не найдено: list.am заблокировал IP, сменилась вёрстка "
              "или на странице нет объявлений.")
        return

    print(f"✅ Найдено ссылок: {len(result)}")
    print("-" * 50)
    for item_id, post_url in result.items():
        print(f"🆔 {item_id} → 🔗 {post_url}")


if __name__ == "__main__":
    run_test()