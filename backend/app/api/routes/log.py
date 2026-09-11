"""``/log`` routes: create, read (daily/history) and delete log entries.

Macros are computed once, at write time, and read back verbatim.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import queries
from app.db.session import get_db
from app.models.user import User
from app.schemas.log import (
    DailyLogResponse,
    HistoryDay,
    HistoryResponse,
    LogEntryCreate,
    LogEntryOut,
    MacroTotals,
)
from app.services import fdc as fdc_service
from app.services.foods import resolve_food, scale_per_100g

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/log",
    tags=["log"],
    dependencies=[Depends(get_current_user)],
)

MAX_RANGE_DAYS = 366


def _totals_from_entries(entries: List) -> MacroTotals:
    totals = queries.sum_macros(entries)
    return MacroTotals(
        calories_kcal=totals["calories_kcal"],
        protein_g=totals["protein_g"],
        fat_g=totals["fat_g"],
        carbs_g=totals["carbs_g"],
    )


@router.post(
    "",
    response_model=LogEntryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Log a food portion",
)
async def create_log_entry(
    payload: LogEntryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LogEntryOut:
    # Cache-first macro resolution (same path as GET /foods/{fdcId}).
    try:
        food = await resolve_food(db, payload.fdc_id)
    except fdc_service.FdcError as exc:
        db.rollback()
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Food {payload.fdc_id} not found",
            )
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    portion = Decimal(payload.portion_grams).quantize(Decimal("0.01"))
    eaten_at = payload.eaten_at or datetime.now(timezone.utc)

    entry = queries.create_food_log(
        db,
        user_id=user.id,
        fdc_id=food.fdc_id,
        food_name=food.food_name,  # snapshot at log time
        portion_grams=portion,
        calories_kcal=scale_per_100g(food.energy_kcal_per_100g, portion),
        protein_g=scale_per_100g(food.protein_g_per_100g, portion),
        fat_g=scale_per_100g(food.fat_g_per_100g, portion),
        carbs_g=scale_per_100g(food.carbs_g_per_100g, portion),
        eaten_at=eaten_at,
    )
    db.commit()
    db.refresh(entry)
    return LogEntryOut.from_model(entry)


# Some clients post to "/log/"; accept both without a redirect.
router.add_api_route(
    "/",
    create_log_entry,
    methods=["POST"],
    response_model=LogEntryOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)


@router.get(
    "/daily",
    response_model=DailyLogResponse,
    summary="Entries and macro totals for one UTC day",
)
def daily_log(
    date_: date = Query(
        default=None,
        alias="date",
        description="Day to report on (YYYY-MM-DD); defaults to today (UTC)",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DailyLogResponse:
    day = date_ or datetime.now(timezone.utc).date()
    entries = queries.list_food_logs_for_day(db, user_id=user.id, day=day)
    return DailyLogResponse(
        date=day,
        entries=[LogEntryOut.from_model(entry) for entry in entries],
        totals=_totals_from_entries(entries),
    )


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Entries grouped by day over a date range",
)
def history(
    start: date = Query(default=None, description="Inclusive start (YYYY-MM-DD)"),
    end: date = Query(default=None, description="Inclusive end (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HistoryResponse:
    today = datetime.now(timezone.utc).date()
    end_date = end or today
    start_date = start or (end_date - timedelta(days=6))

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start must be on or before end",
        )
    if (end_date - start_date).days > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Date range cannot exceed {MAX_RANGE_DAYS} days",
        )

    grouped = queries.food_logs_grouped_by_day(
        db, user_id=user.id, start_date=start_date, end_date=end_date
    )

    days: List[HistoryDay] = []
    overall = {
        "calories_kcal": Decimal("0.00"),
        "protein_g": Decimal("0.00"),
        "fat_g": Decimal("0.00"),
        "carbs_g": Decimal("0.00"),
    }
    for day in sorted(grouped.keys(), reverse=True):
        entries = grouped[day]
        totals = _totals_from_entries(entries)
        overall["calories_kcal"] += totals.calories_kcal
        overall["protein_g"] += totals.protein_g
        overall["fat_g"] += totals.fat_g
        overall["carbs_g"] += totals.carbs_g
        days.append(
            HistoryDay(
                date=day,
                entries=[LogEntryOut.from_model(entry) for entry in entries],
                totals=totals,
            )
        )

    return HistoryResponse(
        start=start_date,
        end=end_date,
        days=days,
        totals=MacroTotals(**overall),
    )


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one of your own entries",
)
def delete_log_entry(
    entry_id: uuid.UUID = Path(description="Food log entry id"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    deleted = queries.delete_food_log(db, entry_id=entry_id, user_id=user.id)
    if not deleted:
        db.rollback()
        # 404 (not 403) so entries of other users are indistinguishable from
        # entries that do not exist.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found"
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
