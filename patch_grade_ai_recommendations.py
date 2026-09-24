from pathlib import Path
import re

p = Path("backend/app/recommendations.py")
s = p.read_text(encoding="utf-8")

new_relevant = r