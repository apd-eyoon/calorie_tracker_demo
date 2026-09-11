"""Cache-first resolution of FDC foods.

``fdc_foods`` is an insert-once cache: a row is written on the first successful
FDC lookup and never updated afterwards.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.db import queries
from app.models.fdc_food import FdcFood
from app.services.fdc import fetch_food

logger = logging.getLogger(__name__)


async def resolve_food(db: Session, fdc_id: int) -> FdcFood:
    """Return the cached food, fetching (and caching) it from FDC on a miss.

    Raises :class:`app.services.fdc.FdcError` when the upstream call fails.
    """
    cached = queries.get_cached_food(db, fdc_id)
    if cached is not None:
        return cached

    data = await fetch_food(fdc_id)
    food = queries.cache_food(
        db,
        fdc_id=data["fdc_id"],
        food_name=data["food_name"],
        energy_kcal_per_100g=data.get("energy_kcal_per_100g"),
        protein_g_per_100g=data.get("protein_g_per_100g"),
        fat_g_per_100g=data.get("fat_g_per_100g"),
        carbs_g_per_100g=data.get("carbs_g_per_100g"),
    )
    db.commit()
    db.refresh(food)
    return food


ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
QUANT = Decimal("0.01")


def scale_per_100g(value: Optional[Decimal], portion_grams: Decimal) -> Decimal:
    """``(per_100g / 100) * portion_grams`` rounded to 2 dp (0 when unknown)."""
    if value is None:
        return ZERO
    return ((Decimal(value) / HUNDRED) * Decimal(portion_grams)).quantize(QUANT)
