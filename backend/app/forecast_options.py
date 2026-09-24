import csv
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api", tags=["forecast"])

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "gujarat_discovery"
ELIGIBLE = DATA_DIR / "eligible_120_plus.csv"
VALIDATED = DATA_DIR / "validated_price_trend_models.csv"
ALLOWED_CROPS = {"Cotton", "Wheat", "Groundnut", "Rice"}


def _read_csv(path: Path):
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@router.get("/forecast/options")
def forecast_options(crop: str = Query(...)):
    if crop not in ALLOWED_CROPS:
        return {
            "status": "unavailable",
            "crop": crop,
            "records": [],
            "message": "Unsupported crop.",
        }

    eligible = _read_csv(ELIGIBLE)
    validated_rows = _read_csv(VALIDATED)

    validated = {
        (
            row.get("crop", "").strip(),
            row.get("market", "").strip(),
            row.get("variety", "").strip(),
        )
        for row in validated_rows
    }

    records = []
    seen = set()

    for row in eligible:
        if row.get("crop", "").strip() != crop:
            continue

        market = row.get("market", "").strip()
        variety = row.get("variety", "").strip()

        if not market or not variety:
            continue

        key = (crop, market, variety)
        if key in seen:
            continue
        seen.add(key)

        try:
            observed_days = int(row.get("observed_days") or 0)
        except ValueError:
            observed_days = 0

        records.append({
            "market": market,
            "variety": variety,
            "observed_days": observed_days,
            "oldest_date": row.get("oldest_date"),
            "newest_date": row.get("newest_date"),
            "validated": key in validated,
        })

    records.sort(
        key=lambda r: (
            not r["validated"],
            -r["observed_days"],
            r["market"].casefold(),
            r["variety"].casefold(),
        )
    )

    return {
        "status": "available" if records else "unavailable",
        "crop": crop,
        "records": records,
        "market_count": len({r["market"] for r in records}),
        "scope_count": len(records),
        "message": (
            "Markets and varieties come from verified Gujarat historical mandi "
            "coverage with at least 120 observed reporting days. AI forecast is "
            "shown only for combinations whose model passed chronological validation."
            if records
            else "No eligible historical market and variety coverage is available."
        ),
    }
