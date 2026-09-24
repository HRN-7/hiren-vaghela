"""Persist actual AGMARKNET observations without changing legacy price records."""
from datetime import date, datetime
import logging
import math
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from .config import settings
from .db import PriceObservation, engine, now, uid

SOURCE = 'AGMARKNET via data.gov.in'
SOURCE_URL = 'https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi'
SCOPE = ['state','district','market','crop','variety','grade','date','source']
logger = logging.getLogger(__name__)


def normalize(row, crop, state, market=''):
    if row.get('crop') != crop or row.get('state') != state or (market and row.get('market') != market):
        raise ValueError('Observation outside requested scope.')
    result = {}
    for key, length in [('state',60),('district',100),('market',180),('crop',30),('variety',100),('grade',30)]:
        value = row.get(key) or ''
        if not isinstance(value,str) or len(value)>length or (key in ['state','market','crop'] and not value.strip()):
            raise ValueError('Invalid scope field.')
        result[key] = value
    day = date.fromisoformat(row['date'])
    if day > datetime.now(ZoneInfo('Asia/Kolkata')).date():raise ValueError('Future observation.')
    price = float(row['price'])
    if not math.isfinite(price) or price<=0:raise ValueError('Invalid price.')
    for key in ['min','max']:
        value = row.get(key)
        value = None if value is None else float(value)
        if value is not None and (not math.isfinite(value) or value<=0):raise ValueError('Invalid price range.')
        result[key+'_price'] = value
    if result['min_price'] is not None and result['min_price']>price:raise ValueError('Invalid minimum.')
    if result['max_price'] is not None and result['max_price']<price:raise ValueError('Invalid maximum.')
    return {**result,'id':uid(),'date':day,'price':price,'source':SOURCE,'source_url':SOURCE_URL,'fetched_at':now()}


def store_snapshot(db, feed, crop, state, market=''):
    if feed.get('source') != SOURCE or feed.get('status') not in ['current','historical']:
        return {'status':'skipped','stored':0,'rejected':0}
    unique, rejected = {}, 0
    for row in feed.get('records',[]):
        try:
            normalized = normalize(row,crop,state,market)
            unique[tuple(normalized[key] for key in SCOPE)] = normalized
        except (ValueError,TypeError,KeyError):rejected += 1
    if not unique:return {'status':'skipped','stored':0,'rejected':rejected}
    dialect = db.get_bind().dialect.name
    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == 'sqlite':  # Isolated tests; production engine enforces PostgreSQL.
        from sqlalchemy.dialects.sqlite import insert
    else:raise ValueError('Unsupported observation database.')
    statement = insert(PriceObservation).values(list(unique.values()))
    statement = statement.on_conflict_do_update(index_elements=SCOPE,set_={
        key:getattr(statement.excluded,key) for key in ['price','min_price','max_price','source_url','fetched_at']
    })
    db.execute(statement)
    db.commit()
    return {'status':'recorded','stored':len(unique),'rejected':rejected,'truncated':bool(feed.get('truncated'))}


def record_snapshot(feed, crop, state, market=''):
    if not settings().database_url:return {'status':'unconfigured','stored':0}
    try:
        with Session(engine()) as db:return store_snapshot(db,feed,crop,state,market)
    except Exception:
        logger.warning('Market observations could not be saved; published prices remain available.')
        return {'status':'unavailable','stored':0}
