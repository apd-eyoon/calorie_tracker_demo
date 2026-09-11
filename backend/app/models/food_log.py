"""``food_log`` table: one row per logged portion.

Macros are calculated at write time ((per_100g / 100) * portion_grams) and
stored, so reads never recalculate.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.fdc_food import FdcFood
    from app.models.user import User


class FoodLog(Base):
    __tablename__ = "food_log"
    __table_args__ = (
        # Supports "today's entries" and date-range history queries.
        Index("ix_food_log_user_id_eaten_at", "user_id", "eaten_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    fdc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("fdc_foods.fdc_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Snapshot of the food name at log time.
    food_name: Mapped[str] = mapped_column(String(500), nullable=False)
    portion_grams: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    calories_kcal: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    eaten_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="food_logs")
    food: Mapped["FdcFood"] = relationship(back_populates="food_logs")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<FoodLog id={self.id} user_id={self.user_id} "
            f"fdc_id={self.fdc_id} eaten_at={self.eaten_at}>"
        )
