"""Durable, opt-in notification delivery; business events commit with their queue."""
import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import timedelta
import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from .config import settings
from .db import Notification, PushToken, PushDelivery, engine, now, uid

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 6


def notify_user(db, owner_id, text):
    notification = Notification(id=uid(), owner_id=owner_id, text=text[:300])
    db.add(notification)
    # Do not flush the calling business operation before its commit/error handler.
    with db.no_autoflush:
        tokens = list(db.scalars(select(PushToken.token).where(PushToken.owner_id == owner_id)))
    for token in tokens:
        db.add(PushDelivery(notification_id=notification.id, token=token))
    return notification


def remove_token(db, token):
    db.execute(delete(PushDelivery).where(PushDelivery.token == token))
    db.execute(delete(PushToken).where(PushToken.token == token))


def send_push(token, notification_id):
    from firebase_admin import messaging
    from .auth import firebase_app
    # Lock screens receive no account names, contact details or sale information.
    message = messaging.Message(token=token, data={
        'title': 'KrishiLink AI',
        'body': 'You have a new account update. Sign in to view it.',
        'notificationId': notification_id,
    }, webpush=messaging.WebpushConfig(headers={'TTL': '3600'}))
    return messaging.send(message, app=firebase_app())


def deliver_pending(session_factory=None, sender=send_push, clock=now, limit=20):
    factory = session_factory or sessionmaker(engine())
    delivered = 0
    for _ in range(limit):
        current = clock()
        with factory() as db:
            row = db.scalar(select(PushDelivery).where(
                PushDelivery.status.in_(['pending', 'retry', 'processing']),
                PushDelivery.next_attempt_at <= current,
            ).order_by(PushDelivery.next_attempt_at).with_for_update(skip_locked=True).limit(1))
            if row is None:
                break
            notification = db.get(Notification, row.notification_id)
            subscription = db.get(PushToken, row.token)
            if (not notification or not subscription or notification.owner_id != subscription.owner_id
                    or notification.read or row.created_at.replace(tzinfo=current.tzinfo) < current - timedelta(days=7)):
                row.status = 'cancelled'
                db.commit()
                continue
            if row.attempts >= MAX_ATTEMPTS:
                row.status = 'failed'
                db.commit()
                continue
            row.attempts += 1
            row.status = 'processing'
            row.lease_id = uid()
            row.next_attempt_at = current + timedelta(minutes=10)
            delivery_id, lease, token, notification_id = row.id, row.lease_id, row.token, row.notification_id
            db.commit()
        # Network I/O happens outside the claim transaction.
        failure = None
        try:
            sender(token, notification_id)
        except Exception as error:
            failure = error
        with factory() as db:
            row = db.scalar(select(PushDelivery).where(PushDelivery.id == delivery_id,
                            PushDelivery.lease_id == lease).with_for_update())
            if row is None:
                continue  # Unsubscribed or superseded while sending.
            if failure is None:
                row.status, row.sent_at, row.last_error = 'sent', clock(), ''
                delivered += 1
            else:
                from firebase_admin import messaging
                from firebase_admin.exceptions import InvalidArgumentError, PermissionDeniedError
                if isinstance(failure, messaging.UnregisteredError):
                    remove_token(db, token)
                else:
                    permanent = isinstance(failure, (InvalidArgumentError, PermissionDeniedError))
                    row.status = 'failed' if permanent or row.attempts >= MAX_ATTEMPTS else 'retry'
                    row.next_attempt_at = clock() + timedelta(seconds=min(3600, 60 * 2 ** (row.attempts - 1)))
                    row.last_error = type(failure).__name__[:100]  # Never log tokens or provider payloads.
            db.commit()
    return delivered


async def delivery_loop():
    while True:
        try:
            await asyncio.to_thread(deliver_pending)
        except Exception:
            logger.warning('Push queue is temporarily unavailable; delivery will retry.')
        await asyncio.sleep(max(5, settings().push_poll_seconds))


@asynccontextmanager
async def lifespan(app):
    config = settings()
    task = None
    if config.push_delivery_enabled and config.database_url and config.firebase_project_id:
        task = asyncio.create_task(delivery_loop())
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
