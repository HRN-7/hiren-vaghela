import math
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ---------------------------------------------------------
# Load root .env file
#
# providers.py = krishilink-ai/backend/app/providers.py
# .env         = krishilink-ai/.env
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"

load_dotenv(ENV_PATH)

from .config import settings


CACHE = {}
DATA = Path(__file__).resolve().parent.parent / "data"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def unavailable(source, reason):
    return {
        "status": "unavailable",
        "source": source,
        "message": reason,
        "records": [],
    }


async def fetch_json(url, params=None, ttl=600):
    key = (url, str(params))

    saved = CACHE.get(key)

    if saved and time.monotonic() - saved[0] < ttl:
        return saved[1]

    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=False,
    ) as client:

        response = await client.get(
            url,
            params=params,
            headers={
                "User-Agent": "KrishiLinkAI/1.0 (agricultural market research)"
            },
        )

        response.raise_for_status()

        result = response.json()

    if len(CACHE) > 512:
        CACHE.clear()

    CACHE[key] = (time.monotonic(), result)

    return result


# =========================================================
# MARKET PRICE DATA
# Data.gov.in / AGMARKNET
# =========================================================


async def agmarknet_prices(
    crop,
    state="Gujarat",
    market="",
):
    source = "AGMARKNET 2.0"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://agmarknet.gov.in",
        "Referer": "https://agmarknet.gov.in/",
        "User-Agent": "Mozilla/5.0",
    }

    def find_named_id(obj, target, kind):
        target = str(target).strip().casefold()

        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = str(key).casefold()

                if (
                    isinstance(value, str)
                    and value.strip().casefold() == target
                ):
                    valid_name = (
                        kind == "state"
                        and "state" in key_lower
                    ) or (
                        kind == "commodity"
                        and (
                            "cmdt" in key_lower
                            or "commodity" in key_lower
                        )
                    )

                    if valid_name:
                        for id_key in (
                            "id",
                            "state_id",
                            "cmdt_id",
                            "commodity_id",
                        ):
                            raw_id = obj.get(id_key)

                            try:
                                if raw_id is not None:
                                    return int(raw_id)
                            except (TypeError, ValueError):
                                pass

            for value in obj.values():
                found = find_named_id(
                    value,
                    target,
                    kind,
                )
                if found is not None:
                    return found

        elif isinstance(obj, list):
            for item in obj:
                found = find_named_id(
                    item,
                    target,
                    kind,
                )
                if found is not None:
                    return found

        return None

    try:
        from zoneinfo import ZoneInfo

        today = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).date()

        async with httpx.AsyncClient(
            timeout=40,
            headers=headers,
            follow_redirects=True,
        ) as client:

            filters_response = await client.get(
                "https://api.agmarknet.gov.in/v1/"
                "daily-price-arrival/filters"
            )
            filters_response.raise_for_status()

            filters_data = filters_response.json()

            state_id = find_named_id(
                filters_data,
                state,
                "state",
            )

            commodity_id = find_named_id(
                filters_data,
                crop,
                "commodity",
            )

            # Verified IDs for current Gujarat/Cotton demo.
            if (
                state_id is None
                and str(state).casefold() == "gujarat"
            ):
                state_id = 11

            if (
                commodity_id is None
                and str(crop).casefold() == "cotton"
            ):
                commodity_id = 15

            if state_id is None:
                return unavailable(
                    source,
                    f"AGMARKNET state not found: {state}",
                )

            if commodity_id is None:
                return unavailable(
                    source,
                    f"AGMARKNET commodity not found: {crop}",
                )

            previous_year = (
                today.year
                if today.month > 1
                else today.year - 1
            )

            previous_month = (
                today.month - 1
                if today.month > 1
                else 12
            )

            periods = [
                (today.year, today.month),
                (previous_year, previous_month),
            ]

            records = []
            seen = set()

            for year, month_number in periods:

                response = await client.get(
                    "https://api.agmarknet.gov.in/v1/"
                    "prices-and-arrivals/date-wise/"
                    "specific-commodity",
                    params={
                        "year": year,
                        "month": month_number,
                        "stateId": state_id,
                        "commodityId": commodity_id,
                        "includeExcel": "false",
                    },
                )

                response.raise_for_status()
                payload = response.json()

                for market_block in payload.get(
                    "markets",
                    [],
                ):
                    market_name = str(
                        market_block.get(
                            "marketName",
                            "",
                        )
                    ).strip()

                    if not market_name:
                        continue

                    if market:
                        wanted = str(
                            market
                        ).strip().casefold()

                        actual = (
                            market_name.casefold()
                        )

                        if (
                            wanted not in actual
                            and actual not in wanted
                        ):
                            continue

                    for day_block in market_block.get(
                        "dates",
                        [],
                    ):
                        raw_date = day_block.get(
                            "arrivalDate",
                            "",
                        )

                        try:
                            arrival_date = datetime.strptime(
                                raw_date,
                                "%d/%m/%Y",
                            ).date()
                        except (TypeError, ValueError):
                            continue

                        if arrival_date > today:
                            continue

                        for row in day_block.get(
                            "data",
                            [],
                        ):
                            try:
                                min_price = float(
                                    row.get(
                                        "minimumPrice"
                                    )
                                )

                                max_price = float(
                                    row.get(
                                        "maximumPrice"
                                    )
                                )

                                modal_price = float(
                                    row.get(
                                        "modalPrice"
                                    )
                                )

                                if any(
                                    not math.isfinite(v)
                                    or v <= 0
                                    for v in (
                                        min_price,
                                        max_price,
                                        modal_price,
                                    )
                                ):
                                    continue

                                if not (
                                    min_price
                                    <= modal_price
                                    <= max_price
                                ):
                                    continue

                                variety = str(
                                    row.get(
                                        "variety",
                                        "",
                                    )
                                ).strip()

                                key = (
                                    market_name.casefold(),
                                    arrival_date.isoformat(),
                                    variety.casefold(),
                                    min_price,
                                    max_price,
                                    modal_price,
                                )

                                if key in seen:
                                    continue

                                seen.add(key)

                                records.append({
                                    "market": market_name,
                                    "district": "",
                                    "state": state,
                                    "crop": crop,
                                    "commodity": crop,
                                    "variety": variety,
                                    "grade": "",
                                    "min": min_price,
                                    "max": max_price,
                                    "price": modal_price,
                                    "modal_price": modal_price,
                                    "date": arrival_date.isoformat(),
                                    "arrival_date": raw_date,
                                    "arrivals": row.get(
                                        "arrivals"
                                    ),
                                })

                            except (
                                TypeError,
                                ValueError,
                            ):
                                continue

        if not records:
            return unavailable(
                source,
                "No recent AGMARKNET records match this crop and state.",
            )

        records.sort(
            key=lambda row: row["date"],
            reverse=True,
        )

        latest_date = records[0]["date"]

        age_days = (
            today
            - date.fromisoformat(latest_date)
        ).days

        return {
            "status": (
                "current"
                if age_days <= 2
                else "historical"
            ),
            "date": latest_date,
            "fetched_at": stamp(),
            "source": source,
            "source_url": "https://agmarknet.gov.in/",
            "records": records,
            "truncated": False,
        }

    except httpx.HTTPStatusError as error:
        return unavailable(
            source,
            "AGMARKNET request failed with HTTP "
            f"{error.response.status_code}.",
        )

    except httpx.RequestError:
        return unavailable(
            source,
            "Could not connect to AGMARKNET.",
        )

    except Exception as error:
        print(
            "AGMARKNET error:",
            type(error).__name__,
            str(error),
        )

        return unavailable(
            source,
            "AGMARKNET market service is temporarily unavailable.",
        )


async def prices(
    crop,
    state="Gujarat",
    market="",
):
    return await agmarknet_prices(
        crop,
        state,
        market,
    )

    cfg = settings()

    source = "AGMARKNET via data.gov.in"

    if not cfg.data_gov_api_key:
        return unavailable(
            source,
            "Data.gov API key is not configured.",
        )

    if not cfg.data_gov_resource_id:
        return unavailable(
            source,
            "Data.gov resource ID is not configured.",
        )

    params = {
        "api-key": cfg.data_gov_api_key,
        "format": "json",
        "limit": 1000,
        "filters[state]": state,
        "filters[commodity]": crop,
    }

    if market:
        params["filters[market]"] = market

    try:
        records = []
        total = 0
        seen = set()
        read = 0

        from zoneinfo import ZoneInfo

        current_day = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).date()

        for offset in range(0, 5000, 1000):

            data = await fetch_json(
                "https://api.data.gov.in/resource/"
                + cfg.data_gov_resource_id,
                {
                    **params,
                    "offset": offset,
                },
                ttl=900,
            )

            page = data.get("records", [])

            try:
                total = int(
                    data.get(
                        "total",
                        len(page),
                    )
                )
            except (ValueError, TypeError):
                total = len(page)

            read += len(page)

            for row in page:

                try:
                    if (
                        str(row.get("commodity", "")).casefold()
                        != crop.casefold()
                    ):
                        continue

                    if (
                        str(row.get("state", "")).casefold()
                        != state.casefold()
                    ):
                        continue

                    if market and (
                        str(row.get("market", "")).casefold()
                        != market.casefold()
                    ):
                        continue

                    arrival_date = datetime.strptime(
                        row["arrival_date"],
                        "%d/%m/%Y",
                    ).date()

                    modal_price = float(
                        row["modal_price"]
                    )

                    min_price = float(
                        row["min_price"]
                    )

                    max_price = float(
                        row["max_price"]
                    )

                    price_values = [
                        modal_price,
                        min_price,
                        max_price,
                    ]

                    if any(
                        not math.isfinite(value)
                        or value <= 0
                        for value in price_values
                    ):
                        continue

                    if min_price > modal_price:
                        continue

                    if max_price < modal_price:
                        continue

                    if arrival_date > current_day:
                        continue

                    market_name = str(
                        row.get("market", "")
                    ).strip()

                    if not market_name:
                        continue

                    normalized = {
                        "market": market_name,
                        "district": row.get(
                            "district",
                            "",
                        ),
                        "state": row.get(
                            "state",
                            state,
                        ),
                        "crop": crop,
                        "commodity": row.get(
                            "commodity",
                            crop,
                        ),
                        "variety": row.get(
                            "variety",
                            "",
                        ),
                        "grade": row.get(
                            "grade",
                            "",
                        ),
                        "min": min_price,
                        "max": max_price,
                        "price": modal_price,
                        "modal_price": modal_price,
                        "date": arrival_date.isoformat(),
                        "arrival_date": row.get(
                            "arrival_date",
                            "",
                        ),
                        "arrivals": None,
                    }

                    duplicate_key = tuple(
                        str(normalized[key])
                        for key in [
                            "market",
                            "district",
                            "state",
                            "crop",
                            "variety",
                            "grade",
                            "date",
                        ]
                    )

                    if duplicate_key in seen:
                        continue

                    seen.add(duplicate_key)

                    records.append(
                        normalized
                    )

                except (
                    KeyError,
                    ValueError,
                    TypeError,
                ):
                    continue

            if (
                not page
                or read >= total
                or len(page) < 1000
            ):
                break

        if not records:
            return unavailable(
                source,
                "No published records match this crop and location.",
            )

        latest_date = max(
            record["date"]
            for record in records
        )

        age_days = (
            current_day
            - date.fromisoformat(
                latest_date
            )
        ).days

        status = (
            "current"
            if age_days <= 2
            else "historical"
        )

        # Latest records first
        records.sort(
            key=lambda row: row["date"],
            reverse=True,
        )

        return {
            "status": status,
            "date": latest_date,
            "fetched_at": stamp(),
            "source": source,
            "source_url": (
                "https://www.data.gov.in/resource/"
                "current-daily-price-various-commodities-"
                "various-markets-mandi"
            ),
            "records": records,
            "truncated": total > read,
        }

    except httpx.HTTPStatusError as error:

        status_code = (
            error.response.status_code
            if error.response
            else None
        )

        return unavailable(
            source,
            f"Data.gov request failed with HTTP status {status_code}.",
        )

    except httpx.RequestError:

        return unavailable(
            source,
            "Could not connect to Data.gov.in. Please check the internet connection.",
        )

    except Exception as error:

        print(
            "Market data error:",
            type(error).__name__,
            str(error),
        )

        return unavailable(
            source,
            "Market service is temporarily unavailable. Please retry later.",
        )


# =========================================================
# SIMPLE MARKET FETCH FUNCTION
#
# Used for local testing and API endpoints.
# =========================================================

async def fetch_mandi_data(
    commodity: str,
    state: str = "Gujarat",
    limit: int = 100,
):
    result = await prices(
        crop=commodity,
        state=state,
    )

    records = result.get(
        "records",
        [],
    )

    if limit > 0:
        records = records[:limit]

    return {
        "status": result.get(
            "status",
            "unavailable",
        ),
        "source": result.get(
            "source",
            "AGMARKNET via data.gov.in",
        ),
        "commodity": commodity,
        "state": state,
        "count": len(records),
        "date": result.get(
            "date"
        ),
        "fetched_at": result.get(
            "fetched_at"
        ),
        "message": result.get(
            "message"
        ),
        "records": records,
    }


# =========================================================
# WEATHER
# =========================================================

async def weather(
    lat,
    lon,
):
    try:

        data = await fetch_json(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": lat,
                "longitude": lon,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "daily": (
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "timezone": "Asia/Kolkata",
                "forecast_days": 7,
            },
        )

        return {
            "status": "current",
            "source": "Open-Meteo",
            "source_url": "https://open-meteo.com/",
            "fetched_at": stamp(),
            **data,
        }

    except Exception:

        return unavailable(
            "Open-Meteo",
            "Weather could not be refreshed.",
        )


# =========================================================
# ROUTE
# =========================================================

async def route(
    lat,
    lon,
    to_lat,
    to_lon,
):
    try:

        data = await fetch_json(
            (
                f"{settings().osrm_url}"
                f"/route/v1/driving/"
                f"{lon},{lat};"
                f"{to_lon},{to_lat}"
            ),
            {
                "overview": "simplified",
                "geometries": "geojson",
                "alternatives": "false",
            },
            ttl=3600,
        )

        route_data = data[
            "routes"
        ][0]

        return {
            "status": "estimated",
            "source": "OSRM / OpenStreetMap",
            "distance_km": round(
                route_data["distance"]
                / 1000,
                1,
            ),
            "duration_hours": round(
                route_data["duration"]
                / 3600,
                1,
            ),
            "geometry": route_data[
                "geometry"
            ],
            "fetched_at": stamp(),
            "message": (
                "Driving route estimate; live traffic, "
                "truck restrictions, tolls and fuel prices "
                "are not included."
            ),
        }

    except Exception:

        return unavailable(
            "OSRM",
            "Route estimate is temporarily unavailable.",
        )


def distance(
    a,
    b,
    c,
    d,
):
    a, b, c, d = map(
        math.radians,
        (
            a,
            b,
            c,
            d,
        ),
    )

    x = (
        math.sin(
            (c - a) / 2
        )
        ** 2
        + math.cos(a)
        * math.cos(c)
        * math.sin(
            (d - b) / 2
        )
        ** 2
    )

    return round(
        6371
        * 2
        * math.asin(
            min(
                1,
                math.sqrt(x),
            )
        ),
        1,
    )


# =========================================================
# STORAGE
# =========================================================

async def storage(
    lat,
    lon,
    radius,
):
    try:

        query = (
            f"[out:json][timeout:12];"
            f"("
            f'nwr(around:{radius * 1000},{lat},{lon})'
            f'["industrial"="warehouse"]["name"];'
            f'nwr(around:{radius * 1000},{lat},{lon})'
            f'["warehouse"="cold_storage"]["name"];'
            f'nwr(around:{radius * 1000},{lat},{lon})'
            f'["name"~"cold storage",i];'
            f");"
            f"out center 50;"
        )

        data = await fetch_json(
            settings().overpass_url,
            {
                "data": query,
            },
            ttl=3600,
        )

        records = []

        for item in data.get(
            "elements",
            [],
        ):

            tags = item.get(
                "tags",
                {},
            )

            center = item.get(
                "center",
                item,
            )

            latitude = center.get(
                "lat"
            )

            longitude = center.get(
                "lon"
            )

            if (
                latitude is None
                or longitude is None
            ):
                continue

            name = tags.get(
                "name",
                "Storage facility",
            )

            is_cold = (
                "cold"
                in name.lower()
                or tags.get(
                    "warehouse"
                )
                == "cold_storage"
            )

            records.append(
                {
                    "id": (
                        f"osm-"
                        f"{item['type']}-"
                        f"{item['id']}"
                    ),
                    "name": name,
                    "type": (
                        "Cold storage"
                        if is_cold
                        else "Storage facility"
                    ),
                    "location": tags.get(
                        "addr:city",
                        "Location on map",
                    ),
                    "lat": latitude,
                    "lon": longitude,
                    "distance": distance(
                        lat,
                        lon,
                        latitude,
                        longitude,
                    ),
                    "capacity": None,
                    "cost": None,
                    "contact": tags.get(
                        "contact:phone",
                        tags.get(
                            "phone"
                        ),
                    ),
                    "verified": False,
                    "source_url": (
                        "https://www.openstreetmap.org/"
                        f"{item['type']}/"
                        f"{item['id']}"
                    ),
                }
            )

        return {
            "status": "directory",
            "source": "OpenStreetMap contributors",
            "fetched_at": stamp(),
            "message": (
                "Map listings only. Agricultural suitability, "
                "tariff and available capacity must be confirmed. "
                "Distance is straight-line."
            ),
            "records": sorted(
                records,
                key=lambda item: item[
                    "distance"
                ],
            ),
        }

    except Exception:

        return unavailable(
            "OpenStreetMap",
            "Nearby storage listings could not be refreshed.",
        )


# =========================================================
# TRANSPORT
# =========================================================

async def transport():

    url = (
        "https://www.fr8.in/"
        "transport-service/"
        "surat-transport-service/"
        "surat-to-mumbai/"
    )

    try:

        key = ("fr8",)

        saved = CACHE.get(
            key
        )

        if (
            saved
            and time.monotonic()
            - saved[0]
            < 3600
        ):
            return saved[1]

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                url
            )

            response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        rows = []

        for tr in soup.select(
            "tr"
        ):

            cols = [
                td.get_text(
                    " ",
                    strip=True,
                )
                for td in tr.select(
                    "td"
                )
            ]

            if len(cols) < 3:
                continue

            rupees = re.search(
                r"₹\s*([\d,]+)",
                cols[2],
            )

            payload = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:Ton|ton)",
                cols[1],
            )

            if (
                not rupees
                or not payload
            ):
                continue

            rows.append(
                {
                    "id": str(
                        len(rows)
                    ),
                    "name": "FR8",
                    "vehicle": cols[0],
                    "payload_tonnes": float(
                        payload[1]
                    ),
                    "trip_price": int(
                        rupees[1].replace(
                            ",",
                            "",
                        )
                    ),
                    "range": (
                        cols[3]
                        if len(cols) > 3
                        else ""
                    ),
                    "origin": "Surat",
                    "destination": "Mumbai",
                    "distance_km": 320,
                    "contact": None,
                    "source_url": url,
                    "availability": (
                        "Confirm with provider"
                    ),
                }
            )

        if not rows:

            return unavailable(
                "FR8",
                "Published transport rates could not be read. "
                "A confirmed quote is required.",
            )

        result = {
            "status": "published_reference",
            "source": "FR8",
            "source_url": url,
            "fetched_at": stamp(),
            "message": (
                "Published Surat–Mumbai full-truck rates; "
                "not a confirmed quote or live vehicle availability."
            ),
            "records": rows,
        }

        CACHE[key] = (
            time.monotonic(),
            result,
        )

        return result

    except Exception:

        return unavailable(
            "FR8",
            "Transport rates could not be refreshed.",
        )


# =========================================================
# PARTNER SERVICES
# =========================================================

async def partner_services(
    kind,
    lat,
    lon,
):
    cfg = settings()

    if (
        not cfg.partner_data_url
        or not cfg.partner_api_key
    ):
        return None

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                (
                    cfg.partner_data_url.rstrip(
                        "/"
                    )
                    + "/"
                    + kind
                ),
                params={
                    "latitude": lat,
                    "longitude": lon,
                },
                headers={
                    "Authorization": (
                        "Bearer "
                        + cfg.partner_api_key
                    )
                },
            )

            response.raise_for_status()

            data = response.json()

        for record in data[
            "records"
        ]:

            required = [
                "id",
                "name",
                "updated_at",
                "source_url",
            ]

            if not all(
                key in record
                for key in required
            ):
                raise ValueError(
                    "Incomplete source metadata"
                )

            if not str(
                record[
                    "source_url"
                ]
            ).startswith(
                "https://"
            ):
                raise ValueError(
                    "Invalid source URL"
                )

        return {
            "status": "partner_reported",
            "fetched_at": stamp(),
            "source": (
                "Connected service provider"
            ),
            "records": data[
                "records"
            ],
        }

    except Exception:

        return unavailable(
            "Connected service provider",
            "Live service availability could not be confirmed.",
        )

