from typing import Optional, List
from sqlalchemy import select, update, delete, Engine
from sqlalchemy.orm import Session
from list_test.database.models import User, Filter  # Предполагаем, что модели из прошлого шага лежат в models.py

class FilterRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    # --- SELECT (Read) ---
    def get_filter_by_user(self, tg_id: int) -> Optional[Filter]:
        """Получает настройки фильтра конкретного пользователя"""
        with Session(self.engine) as session:
            stmt = select(Filter).where(Filter.user_id == tg_id)
            return session.scalars(stmt).first()

    # --- UPDATE (Update) ---
    def update_filters(self, tg_id: int, filter_data: dict, generated_url: str = None) -> None:
        """
        Обновляет параметры фильтрации, полученные из WebApp JSON.
        Передаем словарь (dict), прилетевший из фронтенда.
        """
        with Session(self.engine) as session:
            with session.begin():
                stmt = (
                    update(Filter)
                    .where(Filter.user_id == tg_id)
                    .values(
                        category_id=filter_data.get("category_id", "62"),
                        post_type=filter_data.get("post_type", "all"),
                        currency_id=filter_data.get("currency_id"),
                        min_price=int(filter_data.get("min_price", 0)),
                        max_price=int(filter_data.get("max_price")) if filter_data.get("max_price") and filter_data.get("max_price") != "Не указана" else None,
                        condition_id=filter_data.get("cnd_id"),
                        seller_id=filter_data.get("user_id"),
                        regions=filter_data.get("regions_ids", []),
                        last_url=generated_url
                    )
                )
                session.execute(stmt)

    def update_last_url(self, tg_id: int, url: str) -> None:
        """Отдельный метод для обновления только поисковой ссылки"""
        with Session(self.engine) as session:
            with session.begin():
                stmt = update(Filter).where(Filter.user_id == tg_id).values(last_url=url)
                session.execute(stmt)

    # --- DELETE (Clear) ---
    def reset_filters(self, tg_id: int) -> None:
        """Сбрасывает фильтры пользователя до дефолтных настроек"""
        with Session(self.engine) as session:
            with session.begin():
                stmt = (
                    update(Filter)
                    .where(Filter.user_id == tg_id)
                    .values(
                        category_id="62",
                        post_type="all",
                        currency_id=None,
                        min_price=0,
                        max_price=None,
                        condition_id=None,
                        seller_id=None,
                        regions=[],
                        last_url=None
                    )
                )
                session.execute(stmt)