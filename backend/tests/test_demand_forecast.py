"""Synthetic fixtures only; no test observations are shipped as live model data."""
import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import numpy as np
import pandas as pd
import pytest

from app.config import settings
from app.demand_forecast import predict_demand, recursive, today
from app.forecast import model_key
import train_demand_model as training


class StepModel:
    def fit(self, x, y):
        return self

    def predict(self, x):
        return np.array([row[0] + 1 for row in x])


def observations(tmp_path):
    dates = pd.date_range(end=today(), periods=140)
    frame = pd.DataFrame({'date': dates.strftime('%Y-%m-%d'), 'demand_quintals': np.arange(140, dtype=float)})
    path = tmp_path / 'test-only-demand.csv'
    frame.to_csv(path, index=False)
    return path, frame


@pytest.mark.parametrize('kind', ['missing', 'duplicate', 'negative', 'nan', 'future'])
def test_rejects_unusable_daily_coverage(tmp_path, kind):
    path, frame = observations(tmp_path)
    if kind == 'missing':frame = frame.drop(50)
    if kind == 'duplicate':frame.loc[50, 'date'] = frame.loc[49, 'date']
    if kind == 'negative':frame.loc[50, 'demand_quintals'] = -1
    if kind == 'nan':frame.loc[50, 'demand_quintals'] = float('nan')
    if kind == 'future':frame.loc[len(frame)-1, 'date'] = str(today() + timedelta(days=1))
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError):training.load_observations(path)


def test_complete_coverage_retains_observed_zero(tmp_path):
    path, _ = observations(tmp_path)
    assert training.load_observations(path).demand_quintals.iloc[0] == 0


def test_recursive_holdout_never_uses_future_actuals():
    class RecordingModel(StepModel):
        def __init__(self):self.lags = []
        def predict(self, x):
            self.lags.append(x[0][0])
            return super().predict(x)
    model = RecordingModel()
    values = [1.] * 7 + [100.] * 7
    dates = [today() + timedelta(days=i) for i in range(14)]
    report = training.evaluate(model, values, dates, 7)
    assert model.lags == [1, 2, 3, 4, 5, 6, 7]
    assert report['mae'] == 95


def test_validated_artifact_exact_scope_and_freshness(tmp_path, monkeypatch):
    path, _ = observations(tmp_path)
    monkeypatch.setattr(training, 'new_model', StepModel)
    monkeypatch.setattr(settings(), 'model_directory', str(tmp_path))
    report = training.train(path, 'Rice', 'Test market', 'Test variety', 'A', 'TEST FIXTURE ONLY', tmp_path)
    assert report['validated'] and report['holdout_days'] == 28
    result = predict_demand('Rice', 'Test market', 'Test variety', 'A')
    assert result['status'] == 'estimated'
    assert len(result['records']) == 7 and result['unit'] == 'quintals'
    assert result['records'][0] == {'date': str(today()+timedelta(days=1)), 'quantity': 140}
    assert predict_demand('Rice', 'Test market', 'Other variety', 'A')['status'] == 'unavailable'
    artifact_path = tmp_path / 'demand' / (model_key('Rice', 'Test market', 'Test variety', 'A') + '.joblib')
    artifact = joblib.load(artifact_path)
    artifact['last_date'] = str(today()-timedelta(days=3))
    joblib.dump(artifact, artifact_path)
    assert predict_demand('Rice', 'Test market', 'Test variety', 'A')['records'] == []
    artifact_path.write_bytes(b'corrupt fixture')
    assert predict_demand('Rice', 'Test market', 'Test variety', 'A')['status'] == 'unavailable'


def test_failed_candidate_never_replaces_existing_model(tmp_path, monkeypatch):
    path, frame = observations(tmp_path)
    frame.demand_quintals = 5
    frame.to_csv(path, index=False)
    monkeypatch.setattr(training, 'new_model', StepModel)
    destination = tmp_path / 'demand' / (model_key('Rice', 'Test market', 'Test variety', 'A') + '.joblib')
    destination.parent.mkdir()
    destination.write_bytes(b'previous trusted artifact')
    result = training.train(path, 'Rice', 'Test market', 'Test variety', 'A', 'TEST FIXTURE ONLY', tmp_path)
    assert not result['validated'] and not result['artifact_written']
    assert destination.read_bytes() == b'previous trusted artifact'


def test_real_xgboost_rejects_candidate_that_cannot_beat_zero_error_baseline(tmp_path):
    path, frame = observations(tmp_path)
    frame.demand_quintals = 0
    frame.to_csv(path, index=False)
    result = training.train(path, 'Rice', 'Test market', 'Test variety', 'A', 'TEST FIXTURE ONLY', tmp_path)
    assert result['baseline_mae'] == 0
    assert result['validated'] is False and result['artifact_written'] is False

