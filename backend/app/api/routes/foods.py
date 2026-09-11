"""``/foods`` routes: authenticated proxy over USDA FoodData Central."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.food import FoodDetail, FoodSearchResult
from app.services import fdc as fdc_service
from app.services.foods import resolve_food

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/foods",
    tags=["foods"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/search",
    response_model=List[FoodSearchResult],
    summary="Search FDC foods (API key stays server-side)",
)
async def search_foods(
    q: str = Query(min_length=1, max_length=200, description="Search term"),
    _user: User = Depends(get_current_user),
) -> List[FoodSearchResult]:
    term = q.strip()
    if not term:
        return []
    try:
        return await fdc_service.search_foods(term)
    except fdc_service.FdcError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get(
    "/{fdc_id}",
    response_model=FoodDetail,
    summary="Per-100g macros for a food (cache-first, FDC fallback)",
)
async def get_food(
    fdc_id: int = Path(gt=0, description="FDC identifier"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> FoodDetail:
    try:
        food = await resolve_food(db, fdc_id)
    except fdc_service.FdcError as exc:
        db.rollback()
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Food {fdc_id} not found",
            )
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    return FoodDetail.from_model(food)
