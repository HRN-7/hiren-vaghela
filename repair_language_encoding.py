from pathlib import Path
import json
import re
import shutil
from datetime import datetime

ROOT = Path.cwd()
I18N = ROOT / "src" / "lib" / "i18n.tsx"
TRANS = ROOT / "src" / "lib" / "translations.json"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

SUSPECT_MARKERS = (
    "àª", "à«", "à¤", "à¥", "â€", "â€¦", "â€™", "â€œ", "â€\x9d",
    "Ã", "Â"
)

def suspicious(s: str) -> bool:
    return any(m in s for m in SUSPECT_MARKERS)

def reverse_mojibake(s: str) -> str:
    """Reverse UTF-8 bytes that were mistakenly decoded as Windows-1252."""
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

def fix_json_value(value):
    if isinstance(value, str):
        return reverse_mojibake(value)
    if isinstance(value, list):
        return [fix_json_value(v) for v in value]
    if isinstance(value, dict):
        return {k: fix_json_value(v) for k, v in value.items()}
    return value

def fix_quoted_ts_strings(text: str) -> str:
    # Touch quoted string contents only; code structure stays unchanged.
    pattern = re.compile(
        r"""(?P<q>['"])(?P<body>(?:\\.|(?!\1).)*?)(?P=q)""",
        re.S
    )

    def repl(match):
        q = match.group("q")
        body = match.group("body")
        fixed = reverse_mojibake(body)
        return q + fixed + q

    return pattern.sub(repl, text)

for path in (I18N, TRANS):
    if not path.is_file():
        raise SystemExit(f"Missing file: {path}")

# Back up ONLY the two language files.
i18n_backup = I18N.with_name(f"i18n.before_language_fix_{STAMP}.tsx")
trans_backup = TRANS.with_name(f"translations.before_language_fix_{STAMP}.json")
shutil.copy2(I18N, i18n_backup)
shutil.copy2(TRANS, trans_backup)

# Repair i18n.tsx quoted translation strings only.
i18n_text = I18N.read_text(encoding="utf-8")
fixed_i18n = fix_quoted_ts_strings(i18n_text)
I18N.write_text(fixed_i18n, encoding="utf-8", newline="\n")

# Repair translations.json values only and validate JSON before writing.
data = json.loads(TRANS.read_text(encoding="utf-8"))
fixed_data = fix_json_value(data)
TRANS.write_text(
    json.dumps(fixed_data, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)

print("Language encoding repair complete.")
print("Changed ONLY:")
print("  src/lib/i18n.tsx")
print("  src/lib/translations.json")
print("Backups:")
print(f"  {i18n_backup}")
print(f"  {trans_backup}")
