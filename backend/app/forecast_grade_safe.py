from pathlib import Path
from datetime import date, timedelta
import hashlib
import math

from .config import settings

TREND_GRADE_KEY = "TREND_ONLY"


def model_key(crop, market, variety, grade):
    return hashlib.sha256(
        "|".join([crop, market, variety, grade]).encode()
    ).hexdigest()


def _predict_one(model, features):
    try:
        import xgboost as xgb
        if isinstance(model, xgb.Booster):
            matrix = xgb.DMatrix([features])
            return float(model.predict(matrix)[0])
    except Exception:
        pass
    return float(model.predict([features])[0])


def _artifact_path(crop, market, variety, grade):
    return (
        Path(settings().model_directory)
        / (model_key(crop, market, variety, grade) + ".joblib")
    )


def predict(crop, market, variety, grade):
    unavailable = {
        "status": "unavailable",
        "records": [],
        "demand": [],
        "message": (
            "No validated model is available for this market and variety."
        ),
    }

    # Prefer a truly grade-specific model if one ever exists.
    exact_path = _artifact_path(crop, market, variety, grade)
    trend_path = _artifact_path(crop, market, variety, TREND_GRADE_KEY)

    if exact_path.exists():
        path = exact_path
        grade_specific = True
    elif trend_path.exists():
        path = trend_path
        grade_specific = False
    else:
        return unavailable

    try:
        import joblib
        import numpy as np

        artifact = joblib.load(path)
        scope = artifact.get("scope") or {}

        if (
            scope.get("crop") != crop
            or scope.get("market") != market
            or scope.get("variety") != variety
        ):
            raise ValueError("Model scope does not match request.")

        last = date.fromisoformat(artifact["last_date"])
        age = (date.today() - last).days

        if age < 0 or age > 2:
            return {
                **unavailable,
                "message": (
                    "The model observations are too old for a current forecast."
                ),
            }

        if not artifact.get("validated"):
            return {
                **unavailable,
                "message": "The model has not beaten the holdout baseline.",
            }

        mae = float(artifact["mae"])
        baseline_mae = float(artifact["baseline_mae"])

        if (
            not math.isfinite(mae)
            or not math.isfinite(baseline_mae)
            or mae >= baseline_mae
        ):
            return {
                **unavailable,
                "message": "The model has not beaten the holdout baseline.",
            }

        values = [float(v) for v in artifact["history"]]
        if (
            len(values) != 7
            or not all(math.isfinite(v) and v > 0 for v in values)
        ):
            return {
                **unavailable,
                "message": "The model history is invalid.",
            }

        records = []
        for offset in range(1, 8):
            day = last + timedelta(days=offset)
            feature_row = [
                values[-1],
                values[-7],
                float(np.mean(values[-7:])),
                day.weekday(),
                day.month,
            ]

            price = _predict_one(artifact["model"], feature_row)
            if not math.isfinite(price):
                raise ValueError("Model returned a non-finite price.")

            price = max(0, price)
            values.append(price)

            records.append({
                "date": day.isoformat(),
                "price": round(price, 2),
            })

        if grade_specific:
            grade_basis = (
                "Forecast model scope includes the requested grade."
            )
            recommendation_use = "grade_specific_price_signal"
        else:
            grade_basis = (
                "The historical AGMARKNET series used for this model does not "
                "carry the prototype A/B/C grade label. This forecast is a "
                "market + variety trend signal only. The farmer's A/B/C grade "
                "must still be checked separately before ranking a market or "
                "calculating confirmed net realization."
            )
            recommendation_use = "timing_trend_only"

        return {
            "status": "estimated",
            "records": records,
            "demand": [],
            "grade_specific": grade_specific,
            "requested_grade": grade,
            "recommendation_use": recommendation_use,
            "grade_basis": grade_basis,
            "validation_mae": mae,
            "baseline_mae": baseline_mae,
            "trained_through": artifact["last_date"],
            "training_basis": artifact.get("training_basis"),
            "message": (
                "Recursive 7-day estimate from verified market observations; "
                "not a guaranteed sale price."
            ),
        }

    except Exception:
        return unavailable
