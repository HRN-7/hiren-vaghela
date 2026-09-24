import sys
from pathlib import Path
from datetime import timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import sessionmaker
from firebase_admin.messaging import UnregisteredError
from app.db import Base, User, PushToken, PushDelivery, Notification, now
from app.notifications import notify_user, deliver_pending, remove_token


@pytest.fixture
def factory():
    engine = create_engine('sqlite://')
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, record):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    with sessions() as db:
        db.add_all([User(id='a', name='Farmer A', role='farmer'), User(id='b', name='Buyer B', role='buyer')])
        db.commit()
        db.add_all([PushToken(token='token-a', owner_id='a'), PushToken(token='token-b', owner_id='b')])
        db.commit()
    return sessions


def queue(factory):
    with factory() as db:
        row = notify_user(db, 'a', 'Private account event.')
        db.commit()
        return row.id


def test_queue_is_atomic_and_only_targets_own_opted_in_device(factory):
    with factory() as db:
        notify_user(db, 'a', 'Rolled back business event.')
        db.rollback()
        assert db.scalars(select(Notification)).all() == []
        assert db.scalars(select(PushDelivery)).all() == []
    notification_id = queue(factory)
    sent = []
    assert deliver_pending(factory, lambda token, ident: sent.append((token, ident))) == 1
    assert sent == [('token-a', notification_id)]
    assert deliver_pending(factory, lambda *args: pytest.fail('Duplicate send')) == 0


def test_delivery_retries_then_succeeds(factory):
    queue(factory)
    moment = now()
    def unavailable(*args):raise ConnectionError('provider unavailable')
    assert deliver_pending(factory, unavailable, clock=lambda: moment) == 0
    with factory() as db:
        row = db.scalar(select(PushDelivery))
        assert row.status == 'retry' and row.attempts == 1
        assert row.last_error == 'ConnectionError'
    assert deliver_pending(factory, lambda *args: pytest.fail('Retry too early'), clock=lambda: moment) == 0
    assert deliver_pending(factory, lambda *args: None, clock=lambda: moment + timedelta(minutes=2)) == 1


def test_invalid_token_removal_and_read_cancellation(factory):
    queue(factory)
    def invalid(*args):raise UnregisteredError('test registration expired')
    deliver_pending(factory, invalid)
    with factory() as db:
        assert db.get(PushToken, 'token-a') is None
        assert db.get(PushToken, 'token-b') is not None
        assert db.scalar(select(Notification)) is not None
        db.add(PushToken(token='token-a', owner_id='a'));db.commit()
    ident = queue(factory)
    with factory() as db:
        db.get(Notification, ident).read = True;db.commit()
    assert deliver_pending(factory, lambda *args: pytest.fail('Already read')) == 0
    with factory() as db:assert db.scalar(select(PushDelivery)).status == 'cancelled'


def test_expired_lease_and_unsubscribe(factory):
    queue(factory)
    moment = now()
    with factory() as db:
        row = db.scalar(select(PushDelivery));row.status='processing';row.lease_id='old'
        row.next_attempt_at=moment-timedelta(minutes=1);row.attempts=1;db.commit()
    assert deliver_pending(factory, lambda *args: None, clock=lambda: moment) == 1
    queue(factory)
    with factory() as db:remove_token(db, 'token-a');db.commit()
    assert deliver_pending(factory, lambda *args: pytest.fail('Unsubscribed')) == 0
