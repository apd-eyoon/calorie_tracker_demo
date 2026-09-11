"""Reusable query helpers for the calorie tracker data access layer.

These helpers keep SQL/ORM details out of the API layer. Macro values are read
straight from ``food_log`` - never recalculated.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.fdc_food import FdcFood
from app.models.food_log import FoodLog
from app.models.user import User

ZERO = Decimal("0.00")


# --------------------------------------------------------------------------- #
# users
# --------------------------------------------------------------------------- #
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Case-insensitive lookup of a user by email."""
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.get(User, user_id)


def create_user(db: Session, *, email: str, password_hash: str) -> User:
    """Insert a new user. Caller is responsible for hashing the password."""
    user = User(email=email.strip().lower(), password_hash=password_hash)
    db.add(user)
    db.flush()
    return user


# --------------------------------------------------------------------------- #
# fdc_foods (insert-once cache)
# --------------------------------------------------------------------------- #
def get_cached_food(db: Session, fdc_id: int) -> Optional[FdcFood]:
    """Return the cached FDC food, or ``None`` on a cache miss."""
    return db.get(FdcFood, fdc_id)


def cache_food(
    db: Session,
    *,
    fdc_id: int,
    food_name: str,
    energy_kcal_per_100g: Optional[Decimal] = None,
    protein_g_per_100g: Optional[Decimal] = None,
    fat_g_per_100g: Optional[Decimal] = None,
    carbs_g_per_100g: Optional[Decimal] = None,
) -> FdcFood:
    """Insert a food into the cache once; existing rows are left untouched.

    Uses ``ON CONFLICT (fdc_id) DO NOTHING`` so concurrent cache fills are safe
    and previously cached rows are never overwritten.
    """
    stmt = (
        pg_insert(FdcFood)
        .values(
            fdc_id=fdc_id,
            food_name=food_name,
            energy_kcal_per_100g=energy_kcal_per_100g,
            protein_g_per_100g=protein_g_per_100g,
            fat_g_per_100g=fat_g_per_100g,
            carbs_g_per_100g=carbs_g_per_100g,
        )
        .on_conflict_do_nothing(index_elements=["fdc_id"])
    )
    db.execute(stmt)
    db.flush()
    food = db.get(FdcFood, fdc_id)
    assert food is not None  # row exists either way after the upsert
    return food


# --------------------------------------------------------------------------- #
# food_log
# --------------------------------------------------------------------------- #
def create_food_log(
    db: Session,
    *,
    user_id: uuid.UUID,
    fdc_id: int,
    food_name: str,
    portion_grams: Decimal,
    calories_kcal: Decimal,
    protein_g: Decimal,
    fat_g: Decimal,
    carbs_g: Decimal,
    eaten_at: datetime,
) -> FoodLog:
    """Persist a log entry with macros already calculated at write time."""
    entry = FoodLog(
        user_id=user_id,
        fdc_id=fdc_id,
        food_name=food_name,
        portion_grams=portion_grams,
        calories_kcal=calories_kcal,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
        eaten_at=eaten_at,
    )
    db.add(entry)
    db.flush()
    return entry


def get_food_log(
    db: Session, *, entry_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[FoodLog]:
    """Fetch an entry only if it belongs to the given user."""
    stmt = select(FoodLog).where(
        FoodLog.id == entry_id, FoodLog.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def delete_food_log(db: Session, *, entry_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete an owned entry. Returns ``True`` when a row was removed."""
    entry = get_food_log(db, entry_id=entry_id, user_id=user_id)
    if entry is None:
        return False
    db.delete(entry)
    db.flush()
    return True


def day_bounds(day: date) -> Tuple[datetime, datetime]:
    """Return the UTC ``[start, end)`` timestamps covering ``day``."""
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def list_food_logs_between(
    db: Session,
    *,
    user_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> List[FoodLog]:
    """Entries with ``start <= eaten_at < end``, oldest first.

    Hits the ``ix_food_log_user_id_eaten_at`` composite index.
    """
    stmt = (
        select(FoodLog)
        .where(
            FoodLog.user_id == user_id,
            FoodLog.eaten_at >= start,
            FoodLog.eaten_at < end,
        )
        .order_by(FoodLog.eaten_at.asc(), FoodLog.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


def list_food_logs_for_day(
    db: Session, *, user_id: uuid.UUID, day: date
) -> List[FoodLog]:
    start, end = day_bounds(day)
    return list_food_logs_between(db, user_id=user_id, start=start, end=end)


def sum_macros(entries: Iterable[FoodLog]) -> Dict[str, Decimal]:
    """Aggregate stored macro columns for a set of entries."""
    totals = {
        "calories_kcal": ZERO,
        "protein_g": ZERO,
        "fat_g": ZERO,
        "carbs_g": ZERO,
    }
    for entry in entries:
        totals["calories_kcal"] += entry.calories_kcal or ZERO
        totals["protein_g"] += entry.protein_g or ZERO
        totals["fat_g"] += entry.fat_g or ZERO
        totals["carbs_g"] += entry.carbs_g or ZERO
    return totals


def daily_totals(
    db: Session, *, user_id: uuid.UUID, day: date
) -> Dict[str, Decimal]:
    """Macro totals for a single UTC day, computed in the database."""
    start, end = day_bounds(day)
    stmt = select(
        func.coalesce(func.sum(FoodLog.calories_kcal), 0),
        func.coalesce(func.sum(FoodLog.protein_g), 0),
        func.coalesce(func.sum(FoodLog.fat_g), 0),
        func.coalesce(func.sum(FoodLog.carbs_g), 0),
    ).where(
        FoodLog.user_id == user_id,
        FoodLog.eaten_at >= start,
        FoodLog.eaten_at < end,
    )
    calories, protein, fat, carbs = db.execute(stmt).one()
    return {
        "calories_kcal": Decimal(calories),
        "protein_g": Decimal(protein),
        "fat_g": Decimal(fat),
        "carbs_g": Decimal(carbs),
    }


def food_logs_grouped_by_day(
    db: Session,
    *,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> Dict[date, List[FoodLog]]:
    """Entries for an inclusive date range, grouped by UTC calendar day."""
    start, _ = day_bounds(start_date)
    _, end = day_bounds(end_date)
    entries = list_food_logs_between(db, user_id=user_id, start=start, end=end)

    grouped: Dict[date, List[FoodLog]] = {}
    for entry in entries:
        eaten_at = entry.eaten_at
        if eaten_at.tzinfo is None:
            eaten_at = eaten_at.replace(tzinfo=timezone.utc)
        grouped.setdefault(eaten_at.astimezone(timezone.utc).date(), []).append(
            entry
        )
    return grouped


def daily_totals_by_day(
    db: Session,
    *,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> Sequence[Tuple[date, Decimal, Decimal, Decimal, Decimal]]:
    """Per-day macro totals over an inclusive date range, ordered by day."""
    start, _ = day_bounds(start_date)
    _, end = day_bounds(end_date)
    day_col = func.date_trunc("day", func.timezone("UTC", FoodLog.eaten_at))
    stmt = (
        select(
            day_col.label("day"),
            func.coalesce(func.sum(FoodLog.calories_kcal), 0),
            func.coalesce(func.sum(FoodLog.protein_g), 0),
            func.coalesce(func.sum(FoodLog.fat_g), 0),
            func.coalesce(func.sum(FoodLog.carbs_g), 0),
        )
        .where(
            FoodLog.user_id == user_id,
            FoodLog.eaten_at >= start,
            FoodLog.eaten_at < end,
        )
        .group_by(day_col)
        .order_by(day_col)
    )
    return [
        (row[0].date(), Decimal(row[1]), Decimal(row[2]), Decimal(row[3]), Decimal(row[4]))
        for row in db.execute(stmt).all()
    ]
