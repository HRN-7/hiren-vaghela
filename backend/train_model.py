"""Train a price model on verified observed mandi days only.

Required CSV columns:
date,price

Rules:
- One exact crop / market / variety / grade per model.
- At least 120 verified observed market days.
- Missing/non-trading days are NOT filled or imputed.
- Model must beat the previous-observation baseline before an artifact is written.
"""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from app.forecast import model_key
from app.config import settings


def mae(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(actual - predicted)))


def train_native_xgboost(x, y):
    matrix = xgb.DMatrix(
        np.asarray(x, dtype=float),
        label=np.asarray(y, dtype=float)
    )

    return xgb.train(
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


def predict_native(model, x):
    matrix = xgb.DMatrix(np.asarray(x, dtype=float))
    return model.predict(matrix)


parser = argparse.ArgumentParser()

parser.add_argument('--csv', required=True)
parser.add_argument(
    '--crop',
    choices=['Cotton', 'Wheat', 'Groundnut', 'Rice'],
    required=True
)
parser.add_argument('--market', required=True)
parser.add_argument('--variety', required=True)
parser.add_argument('--grade', required=True)

args = parser.parse_args()

df = pd.read_csv(args.csv)

if not {'date', 'price'}.issubset(df.columns):
    raise ValueError('Required CSV columns: date,price.')

df['date'] = pd.to_datetime(
    df['date'],
    format='%Y-%m-%d',
    errors='raise'
)

df['price'] = pd.to_numeric(
    df['price'],
    errors='raise'
)

df = df.sort_values('date').reset_index(drop=True)

if df['date'].duplicated().any():
    raise ValueError(
        'Each observed market date must appear only once.'
    )

if (
    (df['price'] <= 0).any()
    or not np.isfinite(df['price']).all()
):
    raise ValueError(
        'Observed prices must be finite and positive.'
    )

if df['date'].max().date() > pd.Timestamp.now().date():
    raise ValueError('Future observations are not permitted.')

if len(df) < 120:
    raise ValueError(
        'At least 120 verified observed market days are required.'
    )

# Lags refer to previous published market observations,
# not synthetic calendar-day values.
df['lag1'] = df['price'].shift(1)
df['lag7'] = df['price'].shift(7)
df['mean7'] = df['price'].shift(1).rolling(7).mean()
df['weekday'] = df['date'].dt.dayofweek
df['month'] = df['date'].dt.month

features = [
    'lag1',
    'lag7',
    'mean7',
    'weekday',
    'month'
]

ready = df.dropna().reset_index(drop=True)

if len(ready) < 90:
    raise ValueError(
        'Insufficient complete observed-price windows.'
    )

split = int(len(ready) * 0.8)

if split < 30 or len(ready) - split < 20:
    raise ValueError(
        'Insufficient chronological train/holdout coverage.'
    )

train = ready.iloc[:split]
test = ready.iloc[split:]

candidate = train_native_xgboost(
    train[features].to_numpy(),
    train['price'].to_numpy()
)

predicted = predict_native(
    candidate,
    test[features].to_numpy()
)

model_mae = mae(
    test['price'].to_numpy(),
    predicted
)

baseline_mae = mae(
    test['price'].to_numpy(),
    test['lag1'].to_numpy()
)

validated = (
    np.isfinite(model_mae)
    and np.isfinite(baseline_mae)
    and model_mae < baseline_mae
)

report = {
    'observed_days': len(df),
    'usable_windows': len(ready),
    'holdout_days': len(test),
    'holdout_mae': model_mae,
    'baseline_mae': baseline_mae,
    'validated': bool(validated),
    'artifact_written': False
}

if not validated:
    print(report)
    raise SystemExit(2)

final_model = train_native_xgboost(
    ready[features].to_numpy(),
    ready['price'].to_numpy()
)

output = Path(settings().model_directory)
output.mkdir(parents=True, exist_ok=True)

destination = (
    output
    / (
        model_key(
            args.crop,
            args.market,
            args.variety,
            args.grade
        )
        + '.joblib'
    )
)

artifact = {
    'model': final_model,
    'mae': model_mae,
    'baseline_mae': baseline_mae,
    'validated': True,
    'last_date': str(df['date'].iloc[-1].date()),
    'history': df['price'].tail(7).astype(float).tolist(),
    'scope': {
        'crop': args.crop,
        'market': args.market,
        'variety': args.variety,
        'grade': args.grade
    },
    'training_basis': 'verified observed mandi days; missing days not imputed'
}

joblib.dump(
    artifact,
    destination
)

report['artifact_written'] = True
report['artifact'] = str(destination)

print(report)
