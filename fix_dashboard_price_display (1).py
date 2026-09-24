from pathlib import Path
import shutil

p = Path("src/pages/Dashboard.tsx")

if not p.is_file():
    raise SystemExit(f"Missing file: {p}")

backup = p.with_name("Dashboard.price-backup.tsx")
if not backup.exists():
    shutil.copy2(p, backup)

s = p.read_text(encoding="utf-8")

old1 = "rupee(bestPrice)"
new1 = "(bestPrice==null||!Number.isFinite(Number(bestPrice))?'-':rupee(bestPrice))"

old2 = "rupee(bestNet?.net_per_quintal)"
new2 = "(bestNet?.net_per_quintal==null||!Number.isFinite(Number(bestNet.net_per_quintal))?'-':rupee(bestNet.net_per_quintal))"

old3 = "{i>0&&<small>/ qtl</small>}"
new3 = "{i>0&&String(value)!=='-'&&<small>/ qtl</small>}"

for old, new in ((old1, new1), (old2, new2), (old3, new3)):
    if old not in s:
        raise SystemExit(f"Expected text not found: {old}")
    s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8", newline="\n")

print("Dashboard price display fixed.")
print("Changed ONLY: src/pages/Dashboard.tsx")
print("No price -> -")
print("Price available -> existing rupee formatter + / qtl")
