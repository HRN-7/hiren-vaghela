from pathlib import Path
import re

p = Path("backend/app/recommendations.py")
s = p.read_text(encoding="utf-8")

new_relevant = 'def relevant_prices(feed,context):\n    """Latest per real market; farmer A/B/C grade is carried explicitly."""\n    selected={}\n    requested_variety=norm(context[\'variety\'])\n    requested_grade=norm(context[\'grade\'])\n    unspecified=requested_variety in [\'other\',\'othernotlisted\',\'\']\n    generic={\'\',\'other\',\'others\',\'local\',\'faq\',norm(context[\'name\'])}\n\n    for row in feed.get(\'records\',[]):\n        try:\n            if norm(row[\'crop\'])!=norm(context[\'name\']):continue\n\n            age=(day()-datetime.fromisoformat(row[\'date\']).date()).days\n            if age<0 or age>MAX_PRICE_AGE_DAYS:continue\n\n            price=float(row[\'price\'])\n            if not math.isfinite(price) or price<=0:continue\n\n            variety=norm(row.get(\'variety\',\'\'))\n            reported_grade=norm(row.get(\'grade\',\'\'))\n\n            if not unspecified and variety!=requested_variety and variety not in generic:\n                continue\n\n            if reported_grade in [\'a\',\'b\',\'c\'] and reported_grade!=requested_grade:\n                continue\n\n            grade_verified=(\n                reported_grade in [\'a\',\'b\',\'c\']\n                and reported_grade==requested_grade\n            )\n            exact=not unspecified and variety==requested_variety\n\n            r={\n                **row,\n                \'id\':market_id(row),\n                \'age_days\':age,\n                \'requested_grade\':context[\'grade\'],\n                \'reported_grade\':row.get(\'grade\',\'\'),\n                \'grade_verified\':grade_verified,\n                \'grade_compatibility\':\'verified\' if grade_verified else \'unverified\',\n                \'variety_match\':\'reported variety\' if exact else \'variety not confirmed\',\n                \'grade_match\':(\n                    f"Verified provider grade {context[\'grade\']} match."\n                    if grade_verified\n                    else "Provider grade is not a verified match to the farmer\'s A/B/C grade. Keep this market unconfirmed for net-realization ranking."\n                ),\n                \'source\':feed[\'source\'],\n                \'source_url\':feed.get(\'source_url\',SOURCE_URL),\n                \'fetched_at\':feed.get(\'fetched_at\'),\n                \'price_basis\':\'Published modal price; expected sale price is an estimate.\'\n            }\n\n            current=selected.get(r[\'id\'])\n            order=(\n                int(grade_verified),\n                int(exact),\n                r[\'date\'],\n                norm(r.get(\'variety\',\'\')),\n                norm(r.get(\'grade\',\'\'))\n            )\n            if not current or order>current[0]:\n                selected[r[\'id\']]=(order,r)\n\n        except (KeyError,ValueError,TypeError):\n            continue\n\n    return [item[1] for item in selected.values()]\n\n\ndef market_trend(context,row):\n    """Attach validated AI timing trend when this exact market+variety model exists."""\n    try:\n        from .forecast import predict as predict_price\n\n        result=predict_price(\n            context[\'name\'],\n            row[\'market\'],\n            row.get(\'variety\') or context[\'variety\'],\n            context[\'grade\']\n        )\n\n        records=result.get(\'records\') or []\n\n        if result.get(\'status\')!=\'estimated\' or not records:\n            return {\n                \'status\':\'unavailable\',\n                \'signal\':\'unavailable\',\n                \'grade_specific\':False,\n                \'message\':result.get(\n                    \'message\',\n                    \'No validated AI trend is available for this market and variety.\'\n                )\n            }\n\n        first=float(records[0][\'price\'])\n        last=float(records[-1][\'price\'])\n        change_pct=((last-first)/first*100) if first else 0.0\n\n        if change_pct>0.5:\n            signal=\'rising\'\n        elif change_pct<-0.5:\n            signal=\'falling\'\n        else:\n            signal=\'stable\'\n\n        return {\n            \'status\':\'estimated\',\n            \'signal\':signal,\n            \'change_pct\':round(change_pct,2),\n            \'first_estimate\':round(first,2),\n            \'last_estimate\':round(last,2),\n            \'trained_through\':result.get(\'trained_through\'),\n            \'validation_mae\':result.get(\'validation_mae\'),\n            \'baseline_mae\':result.get(\'baseline_mae\'),\n            \'grade_specific\':bool(result.get(\'grade_specific\')),\n            \'recommendation_use\':result.get(\n                \'recommendation_use\',\n                \'timing_trend_only\'\n            ),\n            \'message\':result.get(\'grade_basis\') or result.get(\'message\')\n        }\n\n    except Exception:\n        return {\n            \'status\':\'unavailable\',\n            \'signal\':\'unavailable\',\n            \'grade_specific\':False,\n            \'message\':\'AI trend could not be loaded for this market.\'\n        }\n'

pattern = r"def relevant_prices\(feed,context\):.*?(?=\nasync def discover\(context\):)"
if not re.search(pattern, s, flags=re.S):
    raise SystemExit("Could not locate relevant_prices() block.")

s = re.sub(pattern, new_relevant + "\n", s, count=1, flags=re.S)

if "row['ai_trend']=market_trend(context,row)" not in s:
    anchor = "row['distance_source']='OSRM / OpenStreetMap'"
    idx = s.find(anchor)
    if idx == -1:
        raise SystemExit("Could not locate route loop to attach ai_trend.")
    line_end = s.find("\n", idx)
    if line_end == -1:
        line_end = len(s)
    insert = "\n        row['ai_trend']=market_trend(context,row)"
    s = s[:line_end] + insert + s[line_end:]

grade_gate = "    if not market.get('grade_verified'):missing.append('Verified A/B/C grade compatibility')\n"
if grade_gate not in s:
    target = "    missing=[];price=market['price'];transport_cost=None;storage_cost=0 if storage_days==0 else None;market_cost=None;other_cost=None;details=[]\n"
    if target not in s:
        raise SystemExit("Could not locate compute_option() cost line.")
    s = s.replace(target, target + grade_gate, 1)

old_warning = "'price_warning':'Your A/B/C grade is self-declared; it is not automatically equivalent to the reported mandi grade. Modal prices are indicative, not sale guarantees.'"
new_warning = "'price_warning':'Farmer A/B/C grade is mandatory. Markets with unverified grade compatibility are not confirmed or ranked for net realization. Modal prices are indicative, not sale guarantees.'"
if old_warning in s:
    s = s.replace(old_warning, new_warning, 1)

p.write_text(s, encoding="utf-8")
print("Applied grade verification + AI trend patch to recommendations.py")
