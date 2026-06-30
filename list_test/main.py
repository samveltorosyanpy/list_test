import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, init_db

# Импортируем роутеры из хэндлеров (напишем их на следующем шаге)
from handlers.commands import router as onboarding_router
from handlers.menu import router as menu_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    # Инициализируем базу данных
    init_db()

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем роутеры (порядок имеет значение!)
    dp.include_router(onboarding_router)
    dp.include_router(menu_router)

    logging.info("Бот успешно запущен и готов к работе...")

    # Запуск пуллинга (сканирования обновлений)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")