import datetime
from typing import List, Optional
from sqlalchemy import BigInteger, ForeignKey, String, Integer, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# Базовый класс для моделей
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # Telegram ID может быть большим числом, используем BigInteger
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    language: Mapped[str] = mapped_column(String(5), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notifications_sound: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    # Отношение один-к-одному с фильтрами
    filter: Mapped[Optional["Filter"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} lang={self.language} active={self.is_active}>"


class Filter(Base):
    __tablename__ = "filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )

    # Поля фильтрации из твоего WebApp
    category_id: Mapped[str] = mapped_column(String(10), default="62")  # Варианты: 62, 63
    post_type: Mapped[str] = mapped_column(String(10), default="all")  # Варианты: all, new
    currency_id: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)

    min_price: Mapped[int] = mapped_column(Integer, default=0)
    max_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    condition_id: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    seller_id: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Храним список ID регионов (районов) в формате JSON (поддерживается и в SQLite, и в Postgres)
    regions: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Готовая сгенерированная ссылка под List.am для парсера
    last_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Обратная связь с пользователем
    user: Mapped["User"] = relationship(back_populates="filter")

    def __repr__(self) -> str:
        return f"<Filter user_id={self.user_id} cat={self.category_id} regions={self.regions}>"