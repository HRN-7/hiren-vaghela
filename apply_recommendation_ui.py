from pathlib import Path

ui = Path("src/pages/Decisions.tsx")
backend = Path("backend/app/recommendations.py")

s = ui.read_text(encoding="utf-8")

old = """<span>{t('Data date')}: {dateLabel(market.date)} · {t(market.variety_match)}</span></div>
  src"""
if old in s:
    raise SystemExit("Unexpected pasted search-output text in Decisions.tsx; aborting.")

target = """<span>{t('Data date')}: {dateLabel(market.date)} · {t(market.variety_match)}</span></div>"""

replacement = """<span>{t('Data date')}: {dateLabel(market.date)} · {t(market.variety_match)}</span><span>{t('Grade compatibility')}: {(market as any).grade_verified?t('Verified'):t('Unverified')}</span><span>{t('AI timing trend')}: {(market as any).ai_trend?.status==='estimated'?`${(market as any).ai_trend.signal} · ${(market as any).ai_trend.change_pct}%`:t('Not validated')}</span></div>{!(market as any).grade_verified&&<Note tone="warm">{t('Farmer grade')} {crop.grade} · {t('Reported grade')}: {market.grade||t('Not reported')}. {t('This market stays unconfirmed for Net Realization until A/B/C grade compatibility is verified.')}</Note>}{(market as any).ai_trend?.status==='estimated'&&<Note>{t('AI timing signal')}: <b>{(market as any).ai_trend.signal}</b> · {(market as any).ai_trend.change_pct}% · {t('Market + variety trend only; not a grade-specific sale-price guarantee.')}</Note>}"""

if target not in s:
    raise SystemExit("Could not find the market facts block in Decisions.tsx.")
s = s.replace(target, replacement, 1)

old_note = """<Note>{t('Your A/B/C quality is self-declared. Mandi grades such as FAQ are shown as reported and are not treated as equivalent.')}</Note>"""
new_note = """<Note>{t('Farmer Grade A/B/C is mandatory for recommendation. FAQ, Local or any other reported mandi grade is not automatically treated as an A/B/C match. Unverified markets can be inspected, but they are not confirmed or ranked as the best Net Realization option.')}</Note>"""
if old_note in s:
    s = s.replace(old_note, new_note, 1)

ui.write_text(s, encoding="utf-8")

b = backend.read_text(encoding="utf-8")
target_b = """    for market in snapshot['records']:
        charges=next((s for s in services['charges'] if s['market_id']==market['id']),None)
"""
replacement_b = """    for market in snapshot['records']:
        if not market.get('grade_verified'):
            continue
        charges=next((s for s in services['charges'] if s['market_id']==market['id']),None)
"""
if target_b in b and "if not market.get('grade_verified'):\n            continue" not in b:
    b = b.replace(target_b, replacement_b, 1)

backend.write_text(b, encoding="utf-8")

print("Updated:")
print("  src/pages/Decisions.tsx")
print("  backend/app/recommendations.py")
print("UI now shows grade compatibility + AI timing status.")
print("Auto-suggestions now exclude unverified A/B/C grade markets.")
