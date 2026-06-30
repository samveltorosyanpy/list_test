from typing import Optional, List
from sqlalchemy import select, update, delete, Engine
from sqlalchemy.orm import Session
from list_test.database.models import User, Filter  # Предполагаем, что модели из прошлого шага лежат в models.py

class UserRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    # --- INSERT (Create) ---
    def create_user(self, tg_id: int, lang: str = "ru") -> User:
        """Создает нового пользователя и инициализирует ему пустой фильтр"""
        with Session(self.engine) as session:
            with session.begin():
                user = User(id=tg_id, language=lang)
                # Сразу создаем пустой связанный фильтр, чтобы потом его только обновлять
                user.filter = Filter(user_id=tg_id)
                session.add(user)
                # Благодаря session.begin() коммит произойдет автоматически
                return user

    # --- SELECT (Read) ---
    def get_user_by_id(self, tg_id: int) -> Optional[User]:
        """Получает пользователя по его Telegram ID"""
        with Session(self.engine) as session:
            stmt = select(User).where(User.id == tg_id)
            return session.scalars(stmt).first()

    def get_all_active_users(self) -> List[User]:
        """Получает всех пользователей, у которых включена слежка"""
        with Session(self.engine) as session:
            stmt = select(User).where(User.is_active == True)
            return list(session.scalars(stmt).all())

    # --- UPDATE (Update) ---
    def update_language(self, tg_id: int, new_lang: str) -> None:
        """Обновляет язык интерфейса пользователя"""
        with Session(self.engine) as session:
            with session.begin():
                stmt = update(User).where(User.id == tg_id).values(language=new_lang)
                session.execute(stmt)

    def toggle_status(self, tg_id: int, is_active: bool) -> None:
        """Включает/выключает слежку (Пауза)"""
        with Session(self.engine) as session:
            with session.begin():
                stmt = update(User).where(User.id == tg_id).values(is_active=is_active)
                session.execute(stmt)

    def toggle_sound(self, tg_id: int, sound_on: bool) -> None:
        """Включает/выключает звук уведомлений"""
        with Session(self.engine) as session:
            with session.begin():
                stmt = update(User).where(User.id == tg_id).values(notifications_sound=sound_on)
                session.execute(stmt)

    # --- DELETE (Delete) ---
    def delete_user(self, tg_id: int) -> bool:
        """Удаляет пользователя (фильтр удалится автоматически благодаря CASCADE)"""
        with Session(self.engine) as session:
            with session.begin():
                stmt = delete(User).where(User.id == tg_id)
                result = session.execute(stmt)
                return result.rowcount > 0