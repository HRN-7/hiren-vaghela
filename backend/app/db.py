from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, Float, Boolean, DateTime, Date, JSON, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from fastapi import HTTPException
from .config import settings

class Base(DeclarativeBase):
    pass

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    location: Mapped[str] = mapped_column(String(150), default='Surat')
    language: Mapped[str] = mapped_column(String(5), default='en')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Crop(Base):
    __tablename__ = 'crops'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(30))
    variety: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(1))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    location: Mapped[str] = mapped_column(String(150))
    sell_date: Mapped[datetime] = mapped_column(Date)
    preferred_market: Mapped[str] = mapped_column(String(150), default='')
    notes: Mapped[str] = mapped_column(String(2000), default='')
    public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Photo(Base):
    __tablename__ = 'crop_photos'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    crop_id: Mapped[str] = mapped_column(ForeignKey('crops.id', ondelete='CASCADE'), index=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    mime: Mapped[str] = mapped_column(String(30), default='image/jpeg')

class Demand(Base):
    __tablename__ = 'buyer_demands'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    company: Mapped[str] = mapped_column(String(160))
    crop: Mapped[str] = mapped_column(String(30))
    grade: Mapped[str] = mapped_column(String(1))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    location: Mapped[str] = mapped_column(String(150))
    required_by: Mapped[datetime] = mapped_column(Date)
    contact: Mapped[str] = mapped_column(String(150))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class FPO(Base):
    __tablename__ = 'fpos'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), unique=True)
    name: Mapped[str] = mapped_column(String(180))
    location: Mapped[str] = mapped_column(String(150))
    members: Mapped[int] = mapped_column(default=0)
    capacity: Mapped[float] = mapped_column(Float, default=0)
    services: Mapped[list] = mapped_column(JSON, default=list)
    contact: Mapped[str] = mapped_column(String(150))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

class FPOContribution(Base):
    __tablename__ = 'fpo_contributions'
    __table_args__ = (UniqueConstraint('fpo_id','crop_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    fpo_id: Mapped[str] = mapped_column(ForeignKey('fpos.id'))
    crop_id: Mapped[str] = mapped_column(ForeignKey('crops.id'))
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)

class Market(Base):
    __tablename__ = 'markets'
    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    state: Mapped[str] = mapped_column(String(60))

class MarketPrice(Base):
    __tablename__ = 'market_prices'
    __table_args__ = (UniqueConstraint('market','crop','variety','grade','date','source'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    market: Mapped[str] = mapped_column(String(180), index=True)
    crop: Mapped[str] = mapped_column(String(30), index=True)
    variety: Mapped[str] = mapped_column(String(100), default='')
    grade: Mapped[str] = mapped_column(String(30), default='')
    date: Mapped[datetime] = mapped_column(Date, index=True)
    price: Mapped[float] = mapped_column(Float)
    arrivals: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(100))

class Record(Base):
    __tablename__ = 'recommendations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class PriceObservation(Base):
    __tablename__ = 'observed_market_prices'
    __table_args__ = (UniqueConstraint('state','district','market','crop','variety','grade','date','source',name='uq_observed_price_scope'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    state: Mapped[str] = mapped_column(String(60), index=True)
    district: Mapped[str] = mapped_column(String(100), default='')
    market: Mapped[str] = mapped_column(String(180), index=True)
    crop: Mapped[str] = mapped_column(String(30), index=True)
    variety: Mapped[str] = mapped_column(String(100), default='')
    grade: Mapped[str] = mapped_column(String(30), default='')
    date: Mapped[datetime] = mapped_column(Date, index=True)
    price: Mapped[float] = mapped_column(Float)
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(String(300))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Connection(Base):
    __tablename__ = 'connections'
    __table_args__ = (UniqueConstraint('owner_id','demand_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    demand_id: Mapped[str] = mapped_column(ForeignKey('buyer_demands.id'))
    message: Mapped[str] = mapped_column(String(1000), default='')

class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    text: Mapped[str] = mapped_column(String(300))
    read: Mapped[bool] = mapped_column(Boolean, default=False)

class PushToken(Base):
    __tablename__ = 'push_tokens'
    token: Mapped[str] = mapped_column(String(500), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)

class PushDelivery(Base):
    __tablename__ = 'push_deliveries'
    __table_args__ = (UniqueConstraint('notification_id', 'token'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    notification_id: Mapped[str] = mapped_column(ForeignKey('notifications.id', ondelete='CASCADE'), index=True)
    token: Mapped[str] = mapped_column(ForeignKey('push_tokens.token', ondelete='CASCADE'))
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    lease_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_error: Mapped[str] = mapped_column(String(100), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ServiceRecord(Base):
    __tablename__ = 'service_records'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

_engine = None

def engine():
    global _engine
    if _engine is None:
        url = settings().database_url
        if not url:
            raise HTTPException(503, 'Account storage is not connected yet. Please try again later.')
        if url.startswith('postgres://'): url = url.replace('postgres://','postgresql+psycopg://',1)
        elif url.startswith('postgresql://'): url = url.replace('postgresql://','postgresql+psycopg://',1)
        if settings().environment == 'production' and not url.startswith('postgresql+psycopg://'):
            raise RuntimeError('Production requires PostgreSQL.')
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine

def get_db():
    with sessionmaker(engine())() as db:
        yield db

class Purchase(Base):
    __tablename__ = 'purchases'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    crop_id: Mapped[str] = mapped_column(ForeignKey('crops.id'), index=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    seller_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    buyer_contact: Mapped[str] = mapped_column(String(150))
    seller_contact: Mapped[str] = mapped_column(String(150), default='')
    message: Mapped[str] = mapped_column(String(1000), default='')
    status: Mapped[str] = mapped_column(String(20), default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
