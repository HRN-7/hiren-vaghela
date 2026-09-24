import sys
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from app.db import Base,PriceObservation,MarketPrice
from app.price_history import SOURCE,store_snapshot


@pytest.fixture
def db():
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as session:yield session


def record(**changes):
    return {'state':'Gujarat','district':'Test district','market':'Test market','crop':'Wheat',
            'variety':'Test variety','grade':'FAQ','date':str(date.today()),'price':2500,'min':2400,'max':2700,**changes}


def feed(*rows):return {'status':'current','source':SOURCE,'records':list(rows)}


def test_observation_upsert_retains_one_row_and_corrected_quote(db):
    for price in [2500,2500,2600]:
        assert store_snapshot(db,feed(record(price=price)),'Wheat','Gujarat')['stored']==1
    rows=db.scalars(select(PriceObservation)).all()
    assert len(rows)==1 and rows[0].price==2600
    assert rows[0].grade=='FAQ'
    assert db.scalars(select(MarketPrice)).all()==[]


def test_out_of_scope_invalid_and_future_rows_are_rejected(db):
    rows=[record(),record(state='Other state'),record(date=str(date.today()+timedelta(days=2))),
          record(price=float('nan')),record(max=float('inf')),record(price=100)]
    result=store_snapshot(db,feed(*rows),'Wheat','Gujarat')
    assert result['stored']==1 and result['rejected']==5
    assert store_snapshot(db,{'status':'historical','source':'Supplied report','records':[record()]},'Wheat','Gujarat')['stored']==0


def test_duplicate_market_names_remain_separate_by_state_and_district(db):
    store_snapshot(db,feed(record()),'Wheat','Gujarat')
    store_snapshot(db,feed(record(district='Other district')),'Wheat','Gujarat')
    store_snapshot(db,feed(record(state='Jammu and Kashmir')),'Wheat','Jammu and Kashmir')
    assert len(db.scalars(select(PriceObservation)).all())==3
