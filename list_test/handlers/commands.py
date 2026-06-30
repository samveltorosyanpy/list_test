from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# Импортируем репозитории и функцию отправки главного меню
from list_test.config import user_repo, filter_repo
from list_test.handlers.menu import send_main_menu

router = Router()

# --- МАРКЕРЫ CALLBACK DATA ---
LANG_PREFIX = "set_lang:"


# --- КЛАВИАТУРЫ ---
def get_lang_keyboard() -> InlineKeyboardMarkup:
    """Генерирует инлайн-кнопки для выбора языка"""
    buttons = [
        [InlineKeyboardButton(text="🇷🇺 Русский (RU)", callback_data=f"{LANG_PREFIX}ru")],
        [InlineKeyboardButton(text="🇦🇲 Հայերեն (AM)", callback_data=f"{LANG_PREFIX}am")],
        [InlineKeyboardButton(text="🇺🇸 English (EN)", callback_data=f"{LANG_PREFIX}en")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- ХԵՆԴԼԵΡЫ ---

@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Хэндлер на команду /start.
    Если пользователь уже зарегистрирован, сразу отправляет Главное Меню.
    Если новый — предлагает выбрать язык.
    """
    tg_user_id = message.from_user.id
    user = user_repo.get_user_by_id(tg_user_id)

    # ЕСЛИ ПОЛЬЗОВАТЕЛЬ УЖЕ ЕСТЬ В БАЗЕ ДАННЫХ
    if user:
        # Сразу отправляем ему его панель управления на его языке
        await send_main_menu(message, tg_id=tg_user_id, lang=user.language)
        return  # Прерываем выполнение хэндлера, чтобы не показывать выбор языка

    # ЕСЛИ ПОЛЬЗОВАТЕЛЬ НОВЫЙ
    welcome_text = (
        "Welcome! Please choose your language to continue.\n\n"
        "Բարի գալուստ: Խնդրում ենք ընտրել լեզուն շարունակելու համար:\n\n"
        "Добро пожаловать! Пожалуйста, выберите язык для продолжения."
    )

    await message.answer(
        text=welcome_text,
        reply_markup=get_lang_keyboard()
    )


@router.callback_query(F.data.startswith(LANG_PREFIX))
async def process_language_choice(callback: CallbackQuery):
    """
    Ловит клик по кнопке выбора языка (только для новых пользователей).
    Регистрирует юзера в БД и отправляет пульт управления.
    """
    chosen_lang = callback.data.split(":")[1]
    tg_user_id = callback.from_user.id

    # Двойная проверка (на случай сбоев): создаем, если пропал, или обновляем
    user = user_repo.get_user_by_id(tg_user_id)
    if not user:
        user_repo.create_user(tg_id=tg_user_id, lang=chosen_lang)
    else:
        user_repo.update_language(tg_id=tg_user_id, new_lang=chosen_lang)

    await callback.answer()

    # Тексты подтверждения
    confirm_texts = {
        "ru": "Отлично! Язык интерфейса изменен на русский. 🇷🇺",
        "am": "Հրաշալի է: Ինտերֆեյսի լեզուն փոխվեց հայերենի: 🇦🇲",
        "en": "Great! Interface language has been changed to English. 🇺🇸"
    }

    # Отправляем короткое подтверждение и удаляем кнопки выбора языка
    await callback.message.answer(text=confirm_texts.get(chosen_lang, confirm_texts["ru"]))
    await callback.message.edit_reply_markup(reply_markup=None)

    # Вызываем полноценный дашборд
    await send_main_menu(callback.message, tg_user_id, chosen_lang)