"""Train on verified daily new buyer-request totals; see docs/FORECASTING.md."""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import os
import tempfile

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from app.config import settings
from app.demand_forecast import TARGET, features, recursive, today
from app.forecast import model_key


def load_observations(path):
    frame = pd.read_csv(path, dtype={'date': str})
    if not {'date', 'demand_quintals'}.issubset(frame.columns):
        raise ValueError('Required CSV columns: date,demand_quintals.')
    if not frame.date.str.fullmatch(r'\d{4}-\d{2}-\d{2}').all():
        raise ValueError('Use ISO dates (YYYY-MM-DD).')
    frame['date'] = pd.to_datetime(frame.date, format='%Y-%m-%d', errors='raise')
    frame['demand_quintals'] = pd.to_numeric(frame.demand_quintals, errors='raise')
    if frame.date.duplicated().any() or not np.isfinite(frame.demand_quintals).all() or (frame.demand_quintals < 0).any():
        raise ValueError('Daily observations must be unique, finite and nonnegative.')
    frame = frame.sort_values('date').reset_index(drop=True)
    if len(frame) < 120:
        raise ValueError('At least 120 observed daily totals are required.')
    if frame.date.iloc[-1].date() > today():
        raise ValueError('Future observations are not permitted.')
    if not frame.date.diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError('Missing days are unknown. Supply complete coverage; do not fill gaps with zeros.')
    return frame


class NativeXGBRegressor:
    def __init__(self):
        self.booster = None

    def fit(self, x, y):
        matrix = xgb.DMatrix(
            np.asarray(x, dtype=float),
            label=np.asarray(y, dtype=float)
        )
        self.booster = xgb.train(
            {
                'objective': 'reg:squarederror',
                'max_depth': 3,
                'eta': 0.04,
                'seed': 42,
                'nthread': 2
            },
            matrix,
            num_boost_round=150
        )
        return self

    def predict(self, x):
        if self.booster is None:
            raise ValueError('Model has not been fitted.')
        matrix = xgb.DMatrix(np.asarray(x, dtype=float))
        return self.booster.predict(matrix)


def new_model():
    return NativeXGBRegressor()


def evaluate(model, values, dates, split):
    """Non-overlapping recursive seven-day holdouts; no future actual features."""
    errors, persistence, seasonal = [], [], []
    for origin in range(split, len(values) - 6, 7):
        estimated = recursive(model, values[:origin], dates[origin], 7)
        for offset, row in enumerate(estimated):
            actual = values[origin + offset]
            errors.append(abs(actual - row['quantity']))
            persistence.append(abs(actual - values[origin - 1]))
            seasonal.append(abs(actual - values[origin - 7 + offset]))
    persistence_mae, seasonal_mae = float(np.mean(persistence)), float(np.mean(seasonal))
    return {'mae': float(np.mean(errors)), 'baseline_mae': min(persistence_mae, seasonal_mae),
            'persistence_mae': persistence_mae, 'seasonal_mae': seasonal_mae,
            'horizon': 7, 'holdout_days': len(errors), 'method': 'recursive_seven_day_holdout'}


def train(csv, crop, market, variety, grade, source, output=None):
    if not source.strip():
        raise ValueError('A verified source and coverage description is required.')
    frame = load_observations(csv)
    values = frame.demand_quintals.astype(float).tolist()
    dates = [d.date() for d in frame.date]
    holdout = max(28, (len(values) // 5 // 7) * 7)
    split = len(values) - holdout
    x = [features(values[:i], dates[i]) for i in range(7, len(values))]
    model = new_model()
    model.fit(x[:split - 7], values[7:split])
    validation = evaluate(model, values, dates, split)
    validated = validation['mae'] < validation['baseline_mae']
    report = {**validation, 'validated': validated, 'observed_days': len(values), 'artifact_written': False}
    if not validated:
        return report  # Preserve any existing artifact; never publish a failed candidate.
    model.fit(x, values[7:])
    scope = {'crop': crop, 'market': market, 'variety': variety, 'grade': grade}
    artifact = {'version': 1, 'target': TARGET, 'scope': scope, 'source': source.strip(),
                'model': model.booster if isinstance(model, NativeXGBRegressor) else model, 'history': values[-7:], 'last_date': dates[-1].isoformat(),
                'validation': validation, 'validated': True}
    directory = Path(output or settings().model_directory) / 'demand'
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / (model_key(crop, market, variety, grade) + '.joblib')
    fd, temporary = tempfile.mkstemp(dir=directory, suffix='.joblib')
    os.close(fd)
    try:
        joblib.dump(artifact, temporary)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {**report, 'artifact_written': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--crop', choices=['Cotton', 'Wheat', 'Groundnut', 'Rice'], required=True)
    for name in ['market', 'variety', 'grade', 'source']:
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    report = train(**vars(args))
    print(json.dumps(report, indent=2))
    return 0 if report['validated'] else 2


if __name__ == '__main__':
    raise SystemExit(main())


