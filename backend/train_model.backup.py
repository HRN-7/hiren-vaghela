"""Train only on a verified CSV for ONE crop / market / variety / grade.
Required columns: date,price. At least 120 daily observations. No synthetic fill.
Usage: python train_model.py --csv prices.csv --crop Rice --market 'Rajkot APMC' --variety 'Basmati' --grade A
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
parser.add_argument('--crop', required=True)
parser.add_argument('--market', required=True)
parser.add_argument('--variety', required=True)
parser.add_argument('--grade', required=True)

args = parser.parse_args()

df = pd.read_csv(args.csv)

df['date'] = pd.to_datetime(df['date'])
df['price'] = pd.to_numeric(df['price'], errors='raise')

if (
    df.date.duplicated().any()
    or (df.price <= 0).any()
    or not np.isfinite(df.price).all()
):
    raise ValueError(
        'Daily observations must be unique, finite and positive.'
    )

if df.date.max().date() > pd.Timestamp.now().date():
    raise ValueError('Future observations are not permitted.')

df = (
    df
    .set_index('date')
    .sort_index()
    .asfreq('D')
)

if len(df.dropna()) < 120:
    raise ValueError(
        'At least 120 observed days are required.'
    )

df['lag1'] = df.price.shift(1)
df['lag7'] = df.price.shift(7)
df['mean7'] = df.price.shift(1).rolling(7).mean()
df['weekday'] = df.index.dayofweek
df['month'] = df.index.month

features = [
    'lag1',
    'lag7',
    'mean7',
    'weekday',
    'month'
]

ready = df.dropna()

if len(ready) < 90 or df.price.tail(7).isna().any():
    raise ValueError(
        'Insufficient complete daily windows. '
        'Missing dates are not imputed.'
    )

split = int(len(ready) * 0.8)

train = ready.iloc[:split]
test = ready.iloc[split:]

model = train_native_xgboost(
    train[features].to_numpy(),
    train.price.to_numpy()
)

predicted = predict_native(
    model,
    test[features].to_numpy()
)

model_mae = mae(
    test.price.to_numpy(),
    predicted
)

baseline_mae = mae(
    test.price.to_numpy(),
    test.lag1.to_numpy()
)

validated = model_mae < baseline_mae

model = train_native_xgboost(
    ready[features].to_numpy(),
    ready.price.to_numpy()
)

output = Path(settings().model_directory)
output.mkdir(parents=True, exist_ok=True)

artifact = {
    'model': model,
    'mae': model_mae,
    'baseline_mae': baseline_mae,
    'validated': validated,
    'last_date': str(df.index[-1].date()),
    'history': df.price.tail(7).tolist(),
    'scope': vars(args)
}

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

joblib.dump(
    artifact,
    destination
)

print({
    'observed_days': len(ready),
    'holdout_days': len(test),
    'holdout_mae': model_mae,
    'baseline_mae': baseline_mae,
    'validated': validated,
    'artifact': str(destination)
})
