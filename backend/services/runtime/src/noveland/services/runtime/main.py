import logging

from noveland.core.database import create_engine_from_settings, create_session_factory
from noveland.core.settings import load_settings
from noveland.events import NatsWorldEventPublisher, WorldEventPublisher
from noveland.services.runtime.clock_tick import RuntimeClockTicker

LOGGER = logging.getLogger("noveland.runtime")


def run_once(publisher: WorldEventPublisher | None = None) -> int:
    settings = load_settings()
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)
    event_publisher = publisher or NatsWorldEventPublisher(settings.nats_url)

    with session_factory() as session:
        result = RuntimeClockTicker(session, event_publisher).run_once()

    LOGGER.info(
        "runtime host tick completed",
        extra={
            "environment": settings.environment,
            "advanced_worlds": result.advanced_worlds,
            "published_events": result.published_events,
        },
    )
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(run_once())
