from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    gender: Mapped[str] = mapped_column(String(32))
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    goal: Mapped[str] = mapped_column(String(64))
    raw_answers: Mapped[dict] = mapped_column(JSON)

    schedules: Mapped[list[UserSchedule]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    macros: Mapped[UserMacros | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )


class UserSchedule(Base):
    __tablename__ = "user_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[str] = mapped_column(String(16), index=True)
    time_start: Mapped[str] = mapped_column(String(16))
    time_end: Mapped[str] = mapped_column(String(16))
    location: Mapped[str] = mapped_column(String(128), index=True)

    user: Mapped[User] = relationship(back_populates="schedules")


class UserMacros(Base):
    __tablename__ = "user_macros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    target_protein_g: Mapped[float] = mapped_column(Float)
    target_carbs_g: Mapped[float] = mapped_column(Float)
    target_fat_g: Mapped[float] = mapped_column(Float)
    target_calories: Mapped[float] = mapped_column(Float)
    strategy_note: Mapped[str] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="macros")


class BoundarySession(Base):
    __tablename__ = "boundary_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    current_step: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class PlanHistory(Base):
    __tablename__ = "plan_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    plan_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    current_plan_text: Mapped[str] = mapped_column(Text)
    structured_plan: Mapped[dict] = mapped_column(JSON, default=dict)
    message_history: Mapped[list[dict]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    change_summary: Mapped[str] = mapped_column(Text, default="")
