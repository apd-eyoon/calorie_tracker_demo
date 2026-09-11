"""Food search / detail schemas.

Note: the FDC API key never appears in any of these models.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class FoodSearchResult(BaseModel):
    """A single row of ``GET /foods/search``."""

    fdcId: int
    name: str
    brandOwner: Optional[str] = None


class FoodDetail(BaseModel):
    """Per-100g macros for one food (cache-first lookup)."""

    fdcId: int
    name: str
    energy_kcal_per_100g: Optional[Decimal] = None
    protein_g_per_100g: Optional[Decimal] = None
    fat_g_per_100g: Optional[Decimal] = None
    carbs_g_per_100g: Optional[Decimal] = None
    cached_at: Optional[datetime] = None

    @classmethod
    def from_model(cls, food) -> "FoodDetail":
        """Build the response from an ``FdcFood`` ORM row."""
        return cls(
            fdcId=food.fdc_id,
            name=food.food_name,
            energy_kcal_per_100g=food.energy_kcal_per_100g,
            protein_g_per_100g=food.protein_g_per_100g,
            fat_g_per_100g=food.fat_g_per_100g,
            carbs_g_per_100g=food.carbs_g_per_100g,
            cached_at=food.cached_at,
        )
