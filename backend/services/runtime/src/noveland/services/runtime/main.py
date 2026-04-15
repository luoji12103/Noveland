import logging

from noveland.core.settings import load_settings

LOGGER = logging.getLogger("noveland.runtime")


def run_once() -> int:
    settings = load_settings()
    LOGGER.info(
        "runtime host initialized",
        extra={"environment": settings.environment},
    )
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(run_once())
