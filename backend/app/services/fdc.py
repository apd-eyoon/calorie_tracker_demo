"""USDA FoodData Central proxy.

The API key lives only on the server (``NUTRITION_API_KEY``) and is attached to
outgoing requests here; it is never included in anything returned to clients.

Nutrients are matched by ``nutrient.number`` (never by name):

* 208 -> energy (kcal)
* 203 -> protein (g)
* 204 -> fat (g)
* 205 -> carbohydrates (g)

All FDC values are per 100 g.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.schemas.food import FoodSearchResult

logger = logging.getLogger(__name__)

NUTRIENT_ENERGY_KCAL = "208"
NUTRIENT_PROTEIN = "203"
NUTRIENT_FAT = "204"
NUTRIENT_CARBS = "205"

NUTRIENT_NUMBERS = [
    NUTRIENT_PROTEIN,
    NUTRIENT_FAT,
    NUTRIENT_CARBS,
    NUTRIENT_ENERGY_KCAL,
]

NUTRIENT_FIELD_BY_NUMBER = {
    NUTRIENT_ENERGY_KCAL: "energy_kcal_per_100g",
    NUTRIENT_PROTEIN: "protein_g_per_100g",
    NUTRIENT_FAT: "fat_g_per_100g",
    NUTRIENT_CARBS: "carbs_g_per_100g",
}


class FdcError(Exception):
    """Raised when the upstream FDC API fails, times out or is misconfigured.

    ``status_code`` is the HTTP status the API should surface to the client
    (502 for upstream failures, 404 when FDC does not know the food).
    """

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _require_api_key() -> str:
    if not settings.nutrition_api_key:
        raise FdcError(
            "Food database is not configured (missing NUTRITION_API_KEY)",
            status_code=502,
        )
    return settings.nutrition_api_key


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    # Column is NUMERIC(8,2) -> keep values in range and at 2 dp.
    if result < Decimal("-999999") or result > Decimal("999999"):
        return None
    return result.quantize(Decimal("0.01"))


def _nutrient_number(nutrient_entry: Dict[str, Any]) -> Optional[str]:
    """Pull the nutrient *number* out of the many FDC payload shapes."""
    for key in ("number", "nutrientNumber"):
        value = nutrient_entry.get(key)
        if value is not None:
            return str(value).strip().lstrip("0") or "0"
    nested = nutrient_entry.get("nutrient")
    if isinstance(nested, dict):
        return _nutrient_number(nested)
    return None


def _nutrient_amount(nutrient_entry: Dict[str, Any]) -> Any:
    for key in ("amount", "value", "nutrientValue"):
        if nutrient_entry.get(key) is not None:
            return nutrient_entry[key]
    return None


def _normalize_number(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    # "208", "0208" and "208.0" should all normalize to "208".
    if raw.endswith(".0"):
        raw = raw[:-2]
    stripped = raw.lstrip("0")
    return stripped or "0"


def extract_macros(payload: Dict[str, Any]) -> Dict[str, Optional[Decimal]]:
    """Extract the four per-100g macros from an FDC food payload."""
    macros: Dict[str, Optional[Decimal]] = {
        "energy_kcal_per_100g": None,
        "protein_g_per_100g": None,
        "fat_g_per_100g": None,
        "carbs_g_per_100g": None,
    }

    nutrients = payload.get("foodNutrients") or []
    if not isinstance(nutrients, list):
        return macros

    for entry in nutrients:
        if not isinstance(entry, dict):
            continue
        number = _normalize_number(_nutrient_number(entry))
        field = NUTRIENT_FIELD_BY_NUMBER.get(number or "")
        if field is None:
            continue
        # Energy appears twice (kcal + kJ) in some payloads: keep kcal only.
        if field == "energy_kcal_per_100g":
            unit = (
                entry.get("unitName")
                or entry.get("nutrientUnit")
                or (entry.get("nutrient") or {}).get("unitName")
                or ""
            )
            if str(unit).strip().lower() in {"kj", "kilojoules"}:
                continue
        if macros[field] is not None:
            continue
        macros[field] = _to_decimal(_nutrient_amount(entry))

    return macros


def food_name_from_payload(payload: Dict[str, Any]) -> str:
    for key in ("description", "lowercaseDescription", "foodDescription"):
        value = payload.get(key)
        if value:
            return str(value)[:500]
    return f"FDC food {payload.get('fdcId', '')}".strip()


async def search_foods(term: str) -> List[FoodSearchResult]:
    """Proxy ``GET /fdc/v1/foods/search`` and normalize the result rows."""
    api_key = _require_api_key()
    url = f"{settings.fdc_base_url}/foods/search"
    params = {
        "query": term,
        "pageSize": settings.fdc_page_size,
        "api_key": api_key,
    }

    payload = await _get_json(url, params, context="food search")

    foods = payload.get("foods") or []
    results: List[FoodSearchResult] = []
    for food in foods:
        if not isinstance(food, dict):
            continue
        fdc_id = food.get("fdcId")
        if fdc_id is None:
            continue
        try:
            fdc_id = int(fdc_id)
        except (TypeError, ValueError):
            continue
        brand = food.get("brandOwner") or food.get("brandName") or None
        results.append(
            FoodSearchResult(
                fdcId=fdc_id,
                name=food_name_from_payload(food),
                brandOwner=str(brand) if brand else None,
            )
        )
    return results[: settings.fdc_page_size]


async def fetch_food(fdc_id: int) -> Dict[str, Any]:
    """Fetch one abridged food from FDC and return name + per-100g macros."""
    api_key = _require_api_key()
    url = f"{settings.fdc_base_url}/food/{fdc_id}"
    params = {
        "format": "abridged",
        "nutrients": ",".join(NUTRIENT_NUMBERS),
        "api_key": api_key,
    }

    payload = await _get_json(url, params, context=f"food {fdc_id}")
    if not isinstance(payload, dict) or not payload:
        raise FdcError(f"Food {fdc_id} not found upstream", status_code=404)

    macros = extract_macros(payload)
    return {
        "fdc_id": fdc_id,
        "food_name": food_name_from_payload(payload),
        **macros,
    }


async def _get_json(url: str, params: Dict[str, Any], *, context: str) -> Any:
    """Perform the upstream GET, mapping every failure mode to ``FdcError``."""
    try:
        async with httpx.AsyncClient(timeout=settings.fdc_timeout_seconds) as client:
            response = await client.get(url, params=params)
    except httpx.TimeoutException as exc:
        logger.warning("FDC timeout during %s: %s", context, exc)
        raise FdcError("Food database request timed out", status_code=502) from exc
    except httpx.HTTPError as exc:
        logger.warning("FDC transport error during %s: %s", context, exc)
        raise FdcError("Food database is unreachable", status_code=502) from exc

    if response.status_code == 404:
        raise FdcError(f"Not found upstream: {context}", status_code=404)
    if response.status_code in (401, 403):
        logger.error("FDC rejected the API key during %s", context)
        raise FdcError("Food database rejected the request", status_code=502)
    if response.status_code == 429:
        raise FdcError("Food database rate limit exceeded", status_code=502)
    if response.status_code >= 400:
        logger.warning(
            "FDC returned %s during %s", response.status_code, context
        )
        raise FdcError("Food database returned an error", status_code=502)

    try:
        return response.json()
    except ValueError as exc:
        raise FdcError("Food database returned an invalid response", 502) from exc
