from pathlib import Path

p = Path("backend/app/recommendations.py")
s = p.read_text(encoding="utf-8")

helper = '''
async def geocode_market(row):
    """Map a mandi conservatively; district fallback is never treated as exact."""
    market = str(row.get("market", "")).strip()
    district = str(row.get("district", "")).strip()
    state = str(row.get("state", "")).strip()

    cleaned_market = market
    for token in [" APMC", "APMC ", " Market Yard", " Mandi"]:
        cleaned_market = cleaned_market.replace(token, " ").strip()

    queries = []
    for q in [
        ", ".join(filter(None, [market, district, state])),
        ", ".join(filter(None, [cleaned_market, district, state])),
        ", ".join(filter(None, [cleaned_market, state])),
    ]:
        if q and q not in queries:
            queries.append(q)

    for q in queries:
        point = await geocode(q)
        if point:
            return {
                **point,
                "market_location_verified": True,
                "market_location_precision": point.get("precision", "mapped market/locality"),
            }

    if district:
        point = await geocode(", ".join(filter(None, [district, state])))
        if point:
            return {
                **point,
                "market_location_verified": False,
                "market_location_precision": "district centroid fallback",
            }

    return None
'''

if "async def geocode_market(row):" not in s:
    marker = "\n\ndef relevant_prices(feed,context):"
    if marker not in s:
        raise SystemExit("Could not find insertion point for geocode_market().")
    s = s.replace(marker, "\n\n" + helper.strip() + marker, 1)

old = '''    for row in candidates[:12]:
        point=await geocode(', '.join(filter(None,[row['market'],row.get('district'),row['state']])))
        if not point:continue
        straight=providers.distance(origin['lat'],origin['lon'],point['lat'],point['lon'])
        if straight>250:continue
        found.append({**row,'coordinates':point,'straight_distance_km':straight})
'''

new = '''    for row in candidates[:12]:
        point=await geocode_market(row)
        if not point:continue
        straight=providers.distance(origin['lat'],origin['lon'],point['lat'],point['lon'])
        if straight>250:continue
        found.append({
            **row,
            'coordinates':point,
            'straight_distance_km':straight,
            'market_location_verified':bool(point.get('market_location_verified')),
            'market_location_precision':point.get('market_location_precision')
        })
'''

if old in s:
    s = s.replace(old, new, 1)
elif "point=await geocode_market(row)" not in s:
    raise SystemExit("Could not find the market-geocoding block to replace.")

old2 = "    if distance is None or not math.isfinite(distance) or distance<0:distance=None;missing.append('Road distance')\n"
new2 = "    if distance is None or not math.isfinite(distance) or distance<0:distance=None;missing.append('Road distance')\n    if not market.get('market_location_verified',True):missing.append('Exact market unloading location')\n"

if old2 in s and "Exact market unloading location" not in s:
    s = s.replace(old2, new2, 1)

p.write_text(s, encoding="utf-8")
print("Patched recommendations.py with safe market geocoding fallback.")
