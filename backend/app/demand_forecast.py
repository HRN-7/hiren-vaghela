"""Exact-scope demand forecasts from operator-verified daily buyer requests.

Arrivals, asking prices, missing days and live listings are never demand labels.
Model files must be created by our training command, never uploaded by a user.
"""
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import logging
import math

from .config import settings
from .forecast import model_key

logger = logging.getLogger(__name__)
TARGET = 'new_buyer_requested_quintals'
MESSAGE = 'No validated demand model is available for this market, variety and grade.'


def today():
    return datetime.now(ZoneInfo('Asia/Kolkata')).date()


def features(history, day):
    return [history[-1], history[-7], sum(history[-7:]) / 7, day.weekday(), day.month]


def _predict_one(model, row):
    """Predict one row with either a native XGBoost Booster or a test/legacy model."""
    try:
        import xgboost as xgb
        if isinstance(model, xgb.Booster):
            matrix = xgb.DMatrix([row])
            return float(model.predict(matrix)[0])
    except Exception:
        pass

    return float(model.predict([row])[0])


def recursive(model, history, start, days=7):
    values = list(history)
    result = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        value = _predict_one(model, features(values, day))
        if not math.isfinite(value):
            raise ValueError('Model returned a non-finite quantity.')
        value = max(0, value)
        values.append(value)
        result.append({'date': day.isoformat(), 'quantity': round(value, 2)})
    return result


def predict_demand(crop, market, variety, grade):
    unavailable = {'status': 'unavailable', 'records': [], 'unit': 'quintals', 'message': MESSAGE}
    path = Path(settings().model_directory) / 'demand' / (model_key(crop, market, variety, grade) + '.joblib')
    if not path.is_file():
        return unavailable
    try:
        import joblib
        artifact = joblib.load(path)  # Trusted operator-created artifacts only.
        scope = {'crop': crop, 'market': market, 'variety': variety, 'grade': grade}
        if artifact.get('version') != 1 or artifact.get('target') != TARGET or artifact.get('scope') != scope:
            raise ValueError('Model scope does not match the request.')
        validation = artifact['validation']
        mae, baseline = validation['mae'], validation['baseline_mae']
        if (
            not artifact.get('validated')
            or not all(math.isfinite(v) and v >= 0 for v in [mae, baseline])
            or mae >= baseline
            or validation.get('horizon') != 7
            or validation.get('holdout_days', 0) < 28
        ):
            return {**unavailable, 'message': 'The demand model has not passed seven-day holdout validation.'}
        last = date.fromisoformat(artifact['last_date'])
        age = (today() - last).days
        if not 0 <= age <= 2:
            return {**unavailable, 'message': 'Recent buyer-demand observations are needed to update this forecast.'}
        history = artifact['history']
        if len(history) != 7 or not all(math.isfinite(v) and v >= 0 for v in history):
            raise ValueError('Invalid demand history.')
        # Bridge any publication delay, but display only dates after today.
        records = recursive(artifact['model'], history, last + timedelta(days=1), 7 + age)[age:]
        return {
            'status': 'estimated',
            'records': records,
            'unit': 'quintals',
            'target': TARGET,
            'validation_mae': mae,
            'baseline_mae': baseline,
            'trained_through': last.isoformat(),
            'source': artifact['source'],
            'validation': validation,
            'message': 'Estimated new buyer requests within the recorded source; not completed sales or total market demand.',
        }
    except Exception:
        logger.warning('Demand model could not be used for the requested scope.')
        return unavailable
