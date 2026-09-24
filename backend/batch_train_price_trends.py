"""Batch-train Gujarat market+variety TREND models for KrishiLink.

These models are NOT grade-specific. They are for timing/trend support only.
Farmer A/B/C grade remains mandatory in the recommendation flow, and a market
must not be confirmed/ranked for net realization unless grade compatibility is
verified separately.

Reads:
  backend/data/gujarat_discovery/eligible_120_plus.csv
  backend/data/gujarat_discovery/series/<crop>/*.csv
"""

from __future__ import annotations

import argparse
import ast
import csv
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DISCOVERY = BACKEND / "data" / "gujarat_discovery"
ELIGIBLE = DISCOVERY / "eligible_120_plus.csv"
SERIES = DISCOVERY / "series"
TRAINER = BACKEND / "train_model.py"

CROPS = ("Cotton", "Wheat", "Groundnut", "Rice")
TREND_GRADE_KEY = "TREND_ONLY"


def slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    return value.strip("_").lower() or "unknown"


def parse_report(stdout: str):
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return ast.literal_eval(line)
            except Exception:
                return None
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-per-crop", type=int, default=4)
    parser.add_argument("--max-age-days", type=int, default=2)
    args = parser.parse_args()

    if not ELIGIBLE.is_file():
        raise FileNotFoundError(
            f"Missing {ELIGIBLE}. Run discover_gujarat_markets.py first."
        )

    with ELIGIBLE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    today = date.today()
    selected = []

    for crop in CROPS:
        candidates = []

        for row in rows:
            if row.get("crop") != crop:
                continue

            try:
                newest = date.fromisoformat(row["newest_date"])
                observed = int(row["observed_days"])
            except Exception:
                continue

            age = (today - newest).days
            if age < 0 or age > args.max_age_days:
                continue

            row["_age"] = age
            row["_observed"] = observed
            candidates.append(row)

        candidates.sort(
            key=lambda r: (
                -r["_observed"],
                r["market"],
                r["variety"],
            )
        )
        selected.extend(candidates[: args.top_per_crop])

    print(f"Selected {len(selected)} recent trend scope(s) for training.")

    passed = []
    failed = []
    missing = []

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)

    for index, row in enumerate(selected, 1):
        crop = row["crop"]
        market = row["market"]
        variety = row["variety"]

        csv_path = (
            SERIES
            / slug(crop)
            / f"{slug(crop)}__{slug(market)}__{slug(variety)}.csv"
        )

        label = f"{crop} | {market} | {variety}"

        if not csv_path.is_file():
            print(f"[{index}/{len(selected)}] MISSING {label}")
            missing.append(label)
            continue

        print(
            f"[{index}/{len(selected)}] Training {label} "
            f"({row['observed_days']} observed days)..."
        )

        command = [
            sys.executable,
            str(TRAINER),
            "--csv",
            str(csv_path),
            "--crop",
            crop,
            "--market",
            market,
            "--variety",
            variety,
            "--grade",
            TREND_GRADE_KEY,
        ]

        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )

        report = parse_report(result.stdout)

        if result.returncode == 0 and report and report.get("artifact_written"):
            print(
                "  PASS "
                f"MAE={report.get('holdout_mae'):.2f} "
                f"baseline={report.get('baseline_mae'):.2f}"
            )
            passed.append({
                "crop": crop,
                "market": market,
                "variety": variety,
                "observed_days": row["observed_days"],
                "newest_date": row["newest_date"],
                "holdout_mae": report.get("holdout_mae"),
                "baseline_mae": report.get("baseline_mae"),
                "model_use": "timing_trend_only",
            })
        else:
            if report:
                print(
                    "  REJECTED "
                    f"MAE={report.get('holdout_mae'):.2f} "
                    f"baseline={report.get('baseline_mae'):.2f}"
                )
            else:
                print("  ERROR")
                if result.stderr.strip():
                    print("   ", result.stderr.strip().splitlines()[-1])
            failed.append(label)

    report_path = DISCOVERY / "validated_price_trend_models.csv"
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "crop",
            "market",
            "variety",
            "observed_days",
            "newest_date",
            "holdout_mae",
            "baseline_mae",
            "model_use",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(passed)

    print("\nBatch trend training complete.")
    print(f"Validated trend models: {len(passed)}")
    print(f"Rejected/failed: {len(failed)}")
    print(f"Missing series files: {len(missing)}")
    print(f"Report: {report_path}")

    for crop in CROPS:
        crop_passed = [r for r in passed if r["crop"] == crop]
        print(f"\nValidated {crop} trend models:")
        if not crop_passed:
            print("  None")
        for row in crop_passed:
            print(
                f"  {row['market']} | {row['variety']} | "
                f"MAE {row['holdout_mae']:.2f} < "
                f"{row['baseline_mae']:.2f}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
