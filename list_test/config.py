import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from database.models import Base
from database.user_repository import UserRepository
from database.filter_repository import FilterRepository

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.db")
engine = create_engine(DATABASE_URL, echo=False)

if not BOT_TOKEN:
    raise ValueError("Переменная BOT_TOKEN не найдена в файле .env!")

# Создаем движок

# Создаем инстансы репозиториев
user_repo = UserRepository(engine)
filter_repo = FilterRepository(engine)

def init_db():
    # Создаем таблицы, если их нет
    Base.metadata.create_all(engine)
    print("База данных проверена и инициализирована.")