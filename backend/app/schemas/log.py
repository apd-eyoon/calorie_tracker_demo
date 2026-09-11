"""Food-log request/response schemas, including ``eaten_at`` validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


def validate_eaten_at(value: datetime) -> datetime:
    """Normalize to UTC and enforce the allowed window.

    * naive datetimes (``datetime-local`` inputs) are interpreted as UTC
    * anything in the future is rejected (small clock-skew tolerance)
    * anything more than ``MAX_PAST_DAYS`` (365) in the past is rejected
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    if value > now + timedelta(seconds=settings.future_skew_seconds):
        raise ValueError("eaten_at cannot be in the future")
    if value < now - timedelta(days=settings.max_past_days):
        raise ValueError(
            f"eaten_at cannot be more than {settings.max_past_days} days in the past"
        )
    return value


class LogEntryCreate(BaseModel):
    fdc_id: int = Field(gt=0, description="USDA FoodData Central identifier")
    portion_grams: Decimal = Field(
        gt=0, le=Decimal("100000"), description="Portion size in grams"
    )
    eaten_at: Optional[datetime] = Field(
        default=None,
        description="When the food was eaten; defaults to server UTC now()",
    )

    @field_validator("eaten_at")
    @classmethod
    def _check_eaten_at(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        return validate_eaten_at(value)


class LogEntryOut(BaseModel):
    id: uuid.UUID
    fdc_id: int
    food_name: str
    portion_grams: Decimal
    calories_kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal
    eaten_at: datetime
    created_at: datetime

    @classmethod
    def from_model(cls, entry) -> "LogEntryOut":
        return cls(
            id=entry.id,
            fdc_id=entry.fdc_id,
            food_name=entry.food_name,
            portion_grams=entry.portion_grams,
            calories_kcal=entry.calories_kcal,
            protein_g=entry.protein_g,
            fat_g=entry.fat_g,
            carbs_g=entry.carbs_g,
            eaten_at=entry.eaten_at,
            created_at=entry.created_at,
        )


class MacroTotals(BaseModel):
    """Sums of the stored macro columns - never recalculated from per-100g."""

    calories_kcal: Decimal = Decimal("0.00")
    protein_g: Decimal = Decimal("0.00")
    fat_g: Decimal = Decimal("0.00")
    carbs_g: Decimal = Decimal("0.00")


class DailyLogResponse(BaseModel):
    date: date
    entries: List[LogEntryOut] = Field(default_factory=list)
    totals: MacroTotals = Field(default_factory=MacroTotals)


class HistoryDay(BaseModel):
    date: date
    entries: List[LogEntryOut] = Field(default_factory=list)
    totals: MacroTotals = Field(default_factory=MacroTotals)


class HistoryResponse(BaseModel):
    start: date
    end: date
    days: List[HistoryDay] = Field(default_factory=list)
    totals: MacroTotals = Field(default_factory=MacroTotals)


class DeleteResponse(BaseModel):
    id: uuid.UUID
    deleted: bool = True
