"""Discover Gujarat-only historical market coverage for KrishiLink crops.

Public source:
    AGMARKNET 2.0 public report API (https://api.agmarknet.gov.in/v1)

This script:
1. Resolves Gujarat and IDs for Cotton, Wheat, Groundnut and Rice.
2. Gets crop-specific Gujarat districts from the public district filter.
3. Downloads date-wise historical market data month by month.
4. Counts verified observed days for each Crop + Market + Variety scope.
5. Writes summary CSV files.
6. Writes one date,price CSV for each scope with at least --min-days observations.

Important:
- Missing/non-trading days are NOT filled.
- No synthetic prices are created.
- Historical rows are grouped by market and variety.
- The date-wise endpoint does not expose the prototype A/B/C grade label,
  so this script does NOT claim grade-specific historical training data.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://api.agmarknet.gov.in/v1"
CROPS = ("Cotton", "Wheat", "Groundnut", "Rice")

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://agmarknet.gov.in",
    "Referer": "https://agmarknet.gov.in/",
    "User-Agent": "Mozilla/5.0",
}


def slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    return value.strip("_").lower() or "unknown"


def pick(d: dict[str, Any], *names: str):
    for name in names:
        if name in d and d[name] not in (None, ""):
            return d[name]
    return None


def request_json(client: httpx.Client, path: str, *, params=None, retries: int = 3):
    url = f"{BASE_URL}{path}"
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError(f"Unexpected JSON shape from {path}")
            return payload
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.25 * attempt)
    raise RuntimeError(f"AGMARKNET request failed: {path}: {last_error}")


def find_list(data: dict[str, Any], token: str) -> list[dict[str, Any]]:
    token = token.lower()
    for key, value in data.items():
        if token in key.lower() and isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    return []


def exact_name_match(rows, target: str, *candidate_keys: str):
    wanted = target.strip().casefold()
    for row in rows:
        for key in candidate_keys:
            value = row.get(key)
            if isinstance(value, str) and value.strip().casefold() == wanted:
                return row
    return None


def month_range(start_year: int, end_year: int, end_month: int):
    for year in range(start_year, end_year + 1):
        last_month = end_month if year == end_year else 12
        for month in range(1, last_month + 1):
            yield year, month


def main() -> int:
    now = datetime.now()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=now.year - 1)
    parser.add_argument("--end-year", type=int, default=now.year)
    parser.add_argument("--end-month", type=int, default=now.month)
    parser.add_argument("--min-days", type=int, default=120)
    parser.add_argument("--output", default="backend/data/gujarat_discovery")
    args = parser.parse_args()

    if args.start_year > args.end_year:
        raise ValueError("start-year must be <= end-year")
    if not 1 <= args.end_month <= 12:
        raise ValueError("end-month must be 1..12")
    if args.min_days < 1:
        raise ValueError("min-days must be positive")

    output = Path(args.output)
    series_dir = output / "series"
    output.mkdir(parents=True, exist_ok=True)
    series_dir.mkdir(parents=True, exist_ok=True)

    timeout = httpx.Timeout(45.0, connect=20.0)

    with httpx.Client(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
        print("Reading AGMARKNET filters...")
        filters_payload = request_json(client, "/daily-price-arrival/filters")
        filter_data = filters_payload.get("data") or {}
        if not isinstance(filter_data, dict):
            raise ValueError("AGMARKNET filters response has no usable data object.")

        commodity_rows = find_list(filter_data, "cmdt")
        state_rows = find_list(filter_data, "state")
        district_rows = find_list(filter_data, "district")
        market_rows = find_list(filter_data, "market")

        gujarat = exact_name_match(state_rows, "Gujarat", "state_name", "name")
        if not gujarat:
            raise ValueError("Could not resolve Gujarat in AGMARKNET filters.")
        state_id = pick(gujarat, "state_id", "id")
        if state_id is None:
            raise ValueError("Gujarat state ID is missing.")

        crop_ids = {}
        for crop in CROPS:
            row = exact_name_match(commodity_rows, crop, "cmdt_name", "commodity_name", "name")
            if not row:
                raise ValueError(f"Could not resolve commodity ID for {crop}.")
            commodity_id = pick(row, "cmdt_id", "commodity_id", "id")
            if commodity_id is None:
                raise ValueError(f"Commodity ID missing for {crop}.")
            crop_ids[crop] = int(commodity_id)

        district_name_by_id = {}
        for row in district_rows:
            did = pick(row, "district_id", "id")
            name = pick(row, "district_name", "name")
            if did is not None and isinstance(name, str):
                try:
                    district_name_by_id[int(did)] = name
                except (TypeError, ValueError):
                    pass

        market_meta_by_name = {}
        for row in market_rows:
            name = pick(row, "market_name", "marketName", "name")
            if isinstance(name, str):
                market_meta_by_name[name.strip().casefold()] = row

        crop_districts = {}
        print(f"Gujarat state ID: {state_id}")
        print("Crop IDs:", ", ".join(f"{c}={crop_ids[c]}" for c in CROPS))

        for crop in CROPS:
            payload = request_json(
                client,
                "/price-trend/district-filter",
                params={
                    "commodity": crop_ids[crop],
                    "report_mode": "marketwise",
                    "state": state_id,
                },
            )
            rows = payload.get("data") or []
            crop_districts[crop] = [r for r in rows if isinstance(r, dict)]
            names = [str(pick(r, "district_name", "name") or "?") for r in crop_districts[crop]]
            print(f"{crop}: {len(names)} district(s): {', '.join(names) if names else 'none'}")

        series = defaultdict(dict)
        periods = list(month_range(args.start_year, args.end_year, args.end_month))
        total_calls = len(CROPS) * len(periods)
        call_no = 0

        for crop in CROPS:
            commodity_id = crop_ids[crop]
            print(f"\nDownloading {crop} history...")
            for year, month in periods:
                call_no += 1
                print(f"  [{call_no}/{total_calls}] {year}-{month:02d}", end="", flush=True)
                try:
                    payload = request_json(
                        client,
                        "/prices-and-arrivals/date-wise/specific-commodity",
                        params={
                            "year": year,
                            "month": month,
                            "stateId": state_id,
                            "commodityId": commodity_id,
                            "includeExcel": "false",
                        },
                    )
                except Exception as exc:
                    print(f" -> ERROR: {exc}")
                    continue

                markets = payload.get("markets") or []
                added = 0
                for market in markets:
                    if not isinstance(market, dict):
                        continue
                    market_name = str(market.get("marketName") or "").strip()
                    if not market_name:
                        continue
                    for date_block in market.get("dates") or []:
                        if not isinstance(date_block, dict):
                            continue
                        raw_date = date_block.get("arrivalDate")
                        if not raw_date:
                            continue
                        try:
                            iso_date = datetime.strptime(str(raw_date), "%d/%m/%Y").strftime("%Y-%m-%d")
                        except ValueError:
                            continue
                        for item in date_block.get("data") or []:
                            if not isinstance(item, dict):
                                continue
                            variety = str(item.get("variety") or "").strip()
                            price = item.get("modalPrice")
                            if not variety or price is None:
                                continue
                            try:
                                price_f = float(price)
                            except (TypeError, ValueError):
                                continue
                            if not math.isfinite(price_f) or price_f <= 0:
                                continue
                            series[(crop, market_name, variety)][iso_date] = price_f
                            added += 1
                print(f" -> {added} price row(s)")

        summary = []
        for (crop, market_name, variety), observations in series.items():
            dates = sorted(observations)
            market_meta = market_meta_by_name.get(market_name.casefold(), {})
            district_id = pick(market_meta, "district_id", "districtId")
            district_name = pick(market_meta, "district_name", "districtName")
            if district_name is None and district_id is not None:
                try:
                    district_name = district_name_by_id.get(int(district_id))
                except (TypeError, ValueError):
                    district_name = None
            district_name = str(district_name) if district_name else "Unknown"
            district_id_text = str(district_id) if district_id is not None else ""

            summary.append({
                "crop": crop,
                "commodity_id": crop_ids[crop],
                "district": district_name,
                "district_id": district_id_text,
                "market": market_name,
                "variety": variety,
                "observed_days": len(dates),
                "oldest_date": dates[0],
                "newest_date": dates[-1],
                "eligible_120": "YES" if len(dates) >= args.min_days else "NO",
            })

            if len(dates) >= args.min_days:
                crop_dir = series_dir / slug(crop)
                crop_dir.mkdir(parents=True, exist_ok=True)
                destination = crop_dir / f"{slug(crop)}__{slug(market_name)}__{slug(variety)}.csv"
                with destination.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["date", "price"])
                    for date_value in dates:
                        writer.writerow([date_value, observations[date_value]])

        summary.sort(key=lambda r: (r["crop"], -int(r["observed_days"]), r["market"], r["variety"]))
        fields = [
            "crop", "commodity_id", "district", "district_id", "market", "variety",
            "observed_days", "oldest_date", "newest_date", "eligible_120",
        ]

        summary_path = output / "gujarat_market_coverage.csv"
        with summary_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(summary)

        eligible = [r for r in summary if int(r["observed_days"]) >= args.min_days]
        eligible_path = output / "eligible_120_plus.csv"
        with eligible_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(eligible)

        district_path = output / "crop_districts.csv"
        with district_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["crop", "commodity_id", "district_id", "district"])
            for crop in CROPS:
                for row in crop_districts[crop]:
                    writer.writerow([
                        crop,
                        crop_ids[crop],
                        pick(row, "district_id", "id") or "",
                        pick(row, "district_name", "name") or "",
                    ])

        print("\nDiscovery complete.")
        print(f"All scopes: {len(summary)}")
        print(f"Eligible scopes (>= {args.min_days} observed days): {len(eligible)}")
        print(f"Summary: {summary_path}")
        print(f"Eligible: {eligible_path}")
        print(f"Crop districts: {district_path}")
        print(f"Eligible series folder: {series_dir}")

        for crop in CROPS:
            best = [r for r in eligible if r["crop"] == crop][:5]
            print(f"\nTop eligible {crop} scopes:")
            if not best:
                print("  None")
            for row in best:
                print(
                    f"  {row['market']} | {row['variety']} | {row['observed_days']} days | "
                    f"{row['oldest_date']} -> {row['newest_date']} | district={row['district']}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
