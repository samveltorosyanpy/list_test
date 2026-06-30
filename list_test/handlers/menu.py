import json
import logging
import urllib.parse
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Подтягиваем репозитории из твоего конфига
from list_test.config import user_repo, filter_repo

router = Router()

WEBAPP_URL = "https://samveltorosyanpy.github.io/list_test/static"

# --- СЛОВАРИ ПЕРЕВОДОВ ПЕРЕВОДОВ ИНТЕРФЕЙСА ---
TEXTS = {
    "ru": {
        "title": "⚙️ **Панель управления снайпером**",
        "status_active": "🟢 **Статус слежки:** Активна",
        "status_paused": "🔴 **Статус слежки:** На паузе",
        "sound_on": "🔊 **Звук уведомлений:** Включен",
        "sound_off": "🔇 **Звук уведомлений:** Выключен",
        "filters_title": "📋 **Текущие фильтры List.am:**",
        "btn_config": "🖥️ Настроить фильтры",
        "btn_mute": "🔕 Выключить звук",
        "btn_unmute": "🔔 Включить звук",
        "btn_pause": "🛑 Пауза",
        "btn_resume": "🚀 Запустить",
    },
    "am": {
        "title": "⚙️ **Սնայպերի կառավարման վահանակ**",
        "status_active": "🟢 **Կարգավիճակ:** Ակտիվ է",
        "status_paused": "🔴 **Կարգավիճակ:** Դադարեցված է",
        "sound_on": "🔊 **Ծանուցումների ձայնը:** Միացված է",
        "sound_off": "🔇 **Ծանուցումների ձայնը:** Անջատված է",
        "filters_title": "📋 **List.am-ի ընթացիկ ֆիլտրերը:**",
        "btn_config": "🖥️ Կարգավորել ֆիլտրերը",
        "btn_mute": "🔕 Անջատել ձայնը",
        "btn_unmute": "🔔 Միացնել ձայնը",
        "btn_pause": "🛑 Դադար",
        "btn_resume": "🚀 Գործարկել",
    },
    "en": {
        "title": "⚙️ **Sniper Control Panel**",
        "status_active": "🟢 **Status:** Active",
        "status_paused": "🔴 **Status:** Paused",
        "sound_on": "🔊 **Notification sound:** On",
        "sound_off": "🔇 **Notification sound:** Off",
        "filters_title": "📋 **Current List.am filters:**",
        "btn_config": "🖥️ Configure Filters",
        "btn_mute": "🔕 Mute",
        "btn_unmute": "🔔 Unmute",
        "btn_pause": "🛑 Pause",
        "btn_resume": "🚀 Resume",
    }
}

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def generate_dashboard_text(tg_id: int, lang: str) -> str:
    """Генерирует текст главного меню на основе актуальных настроек из БД"""
    user = user_repo.get_user_by_id(tg_id)
    user_filter = filter_repo.get_filter_by_user(tg_id)

    t = TEXTS.get(lang, TEXTS["ru"])

    status = t["status_active"] if user.is_active else t["status_paused"]
    sound = t["sound_on"] if user.notifications_sound else t["sound_off"]

    # Извлекаем параметры фильтров для красивого вывода
    category = "Վաճառք (Продажа)" if user_filter.category_id == "62" else "Երկարաժամկետ վարձակալություն (Аренда)"
    post_type = "Բոլորը (Все)" if user_filter.post_type == "all" else "Միայն նոր (Только новые)"

    currency_map = {"0": "AMD", "1": "USD ($)", "2": "EUR (€)", "3": "RUB (₽)"}
    currency = currency_map.get(user_filter.currency_id, "Любая")

    max_p = user_filter.max_price if user_filter.max_price else "∞"

    # Собираем итоговое сообщение
    text = (
        f"{t['title']}\n\n"
        f"{status}\n"
        f"{sound}\n\n"
        f"{t['filters_title']}\n"
        f"🗂 Раздел: {category}\n"
        f"🔄 Лента: {post_type}\n"
        f"💰 Валюта: {currency}\n"
        f"💵 Цена: от {user_filter.min_price} до {max_p}\n"
        f"🔗 Ссылка: {user_filter.last_url or 'Не настроена'}"
    )
    return text


def get_menu_keyboard(tg_id: int, lang: str) -> InlineKeyboardMarkup:
    """Формирует клавиатуру управления и передает текущие фильтры в URL WebApp"""
    user = user_repo.get_user_by_id(tg_id)
    user_filter = filter_repo.get_filter_by_user(tg_id)
    t = TEXTS.get(lang, TEXTS["ru"])

    # Складываем текущие настройки из БД в чистый словарь для хэша
    current_settings = {
        "cat": user_filter.category_id,
        "type": user_filter.post_type,
        "curr": user_filter.currency_id,
        "min": user_filter.min_price,
        "max": user_filter.max_price if user_filter.max_price is not None else "",
        "cnd": user_filter.condition_id,
        "sel": user_filter.seller_id,
        "regions": user_filter.regions  # list ID [11, 12]
    }

    # Переводим словарь в JSON-строку и экранируем для URL
    json_data = json.dumps(current_settings)
    encoded_data = urllib.parse.quote(json_data)
    # Формируем финальный URL с хэшем
    webapp_full_url = f"{WEBAPP_URL}?start_data={encoded_data}"
    print(webapp_full_url)

    sound_btn = InlineKeyboardButton(
        text=t["btn_mute"] if user.notifications_sound else t["btn_unmute"],
        callback_data="toggle_sound"
    )
    status_btn = InlineKeyboardButton(
        text=t["btn_pause"] if user.is_active else t["btn_resume"],
        callback_data="toggle_status"
    )

    buttons = [
        [InlineKeyboardButton(text=t["btn_config"], web_app=WebAppInfo(url=webapp_full_url))],
        [sound_btn, status_btn]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_main_menu(message: Message, tg_id: int, lang: str):
    """Отправка нового сообщения главного меню"""
    text = generate_dashboard_text(tg_id, lang)
    kb = get_menu_keyboard(tg_id, lang)
    await message.answer(text=text, reply_markup=kb, parse_mode="Markdown")


# --- ХЭНДЛЕР ДАННЫХ ИЗ WEBAPP ---

@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    """
    Ловит JSON из WebApp, обновляет таблицу filters и перерисовывает дашборд.
    """
    tg_id = message.from_user.id
    user = user_repo.get_user_by_id(tg_id)

    if not user:
        return

    try:
        # 1. Извлекаем строку из WebApp и превращаем в Python dict
        raw_json = message.web_app_data.data
        filter_data = json.loads(raw_json)

        # 2. Собираем тестовую поисковую ссылку на основе новых данных
        mock_url = f"https://www.list.am/category/{filter_data.get('category_id')}?n=0&price1={filter_data.get('min_price')}"

        # 3. Сохраняем измененные пользователем данные в базу (вызываем твой репозиторий)
        filter_repo.update_filters(
            tg_id=tg_id,
            filter_data=filter_data,
            generated_url=mock_url
        )

        # 4. Удаляем сервисную плашку «Вы отправили данные», чтобы чат выглядел красиво
        await message.delete()

        # 5. Отправляем обновленный пульт управления с новыми ценами и разделами
        await send_main_menu(message, tg_id=tg_id, lang=user.language)

    except Exception as e:
        logging.error(f"Ошибка при обработке данных из WebApp: {e}")
        await message.answer("⚠️ Произошла ошибка при сохранении фильтров.")


# --- ХԵՆԴԼԵՐЫ ПЕРЕКЛЮЧАТЕЛЕЙ (CALLBACK QUERIES) ---

@router.callback_query(F.data == "toggle_sound")
async def handle_toggle_sound(callback: CallbackQuery):
    tg_id = callback.from_user.id
    user = user_repo.get_user_by_id(tg_id)

    user_repo.toggle_sound(tg_id, not user.notifications_sound)
    await callback.answer()

    text = generate_dashboard_text(tg_id, user.language)
    kb = get_menu_keyboard(tg_id, user.language)
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "toggle_status")
async def handle_toggle_status(callback: CallbackQuery):
    tg_id = callback.from_user.id
    user = user_repo.get_user_by_id(tg_id)

    user_repo.toggle_status(tg_id, not user.is_active)
    await callback.answer()

    text = generate_dashboard_text(tg_id, user.language)
    kb = get_menu_keyboard(tg_id, user.language)
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="Markdown")