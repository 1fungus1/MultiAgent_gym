import asyncio
import logging
from contextlib import suppress

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.appointment_service import expire_waitlist_offers
from app.services.attendance_service import mark_no_shows
from app.services.notification_service import notify_expiring_memberships

logger = logging.getLogger(__name__)


def run_maintenance_once() -> None:
    with SessionLocal() as db:
        try:
            expired_offers = expire_waitlist_offers(db)
            no_shows = mark_no_shows(db)
            expiring_notifications = notify_expiring_memberships(db)
            db.commit()
            if expired_offers or no_shows or expiring_notifications:
                logger.info(
                    "Maintenance completed: expired_offers=%s no_shows=%s "
                    "expiry_notifications=%s",
                    expired_offers,
                    no_shows,
                    expiring_notifications,
                )
        except Exception:
            db.rollback()
            logger.exception("Scheduled maintenance failed")


async def maintenance_worker(stop_event: asyncio.Event) -> None:
    await asyncio.to_thread(run_maintenance_once)
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=max(settings.maintenance_interval_seconds, 10),
            )
        except TimeoutError:
            await asyncio.to_thread(run_maintenance_once)


async def stop_maintenance_worker(
    task: asyncio.Task,
    stop_event: asyncio.Event,
) -> None:
    stop_event.set()
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

