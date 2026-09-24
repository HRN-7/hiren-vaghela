from pathlib import Path
import json
import shutil
from datetime import datetime

ROOT = Path.cwd()
TRANS = ROOT / "src" / "lib" / "translations.json"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

SUSPECT_MARKERS = (
    "àª", "à«", "à¤", "à¥", "â€", "â€¦", "â€™", "â€œ", "â€\x9d",
    "Ã", "Â"
)

def suspicious(s: str) -> bool:
    return any(m in s for m in SUSPECT_MARKERS)

def reverse_mojibake(s: str) -> str:
    if not suspicious(s):
        return s

    current = s
    for _ in range(2):
        if not suspicious(current):
            break
        try:
            candidate = current.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if candidate == current:
            break
        current = candidate
    return current

def fix_value(value):
    if isinstance(value, str):
        return reverse_mojibake(value)
    if isinstance(value, list):
        return [fix_value(v) for v in value]
    if isinstance(value, dict):
        return {k: fix_value(v) for k, v in value.items()}
    return value

if not TRANS.is_file():
    raise SystemExit(f"Missing file: {TRANS}")

backup = TRANS.with_name(f"translations.before_bom_fix_{STAMP}.json")
shutil.copy2(TRANS, backup)

# utf-8-sig safely accepts a BOM if present and normal UTF-8 if not.
data = json.loads(TRANS.read_text(encoding="utf-8-sig"))
fixed = fix_value(data)

# Validate by serializing and parsing again before replacing the file.
rendered = json.dumps(fixed, ensure_ascii=False, indent=2) + "\n"
json.loads(rendered)

TRANS.write_text(rendered, encoding="utf-8", newline="\n")

print("translations.json repaired successfully.")
print("Changed ONLY: src/lib/translations.json")
print(f"Backup: {backup}")
