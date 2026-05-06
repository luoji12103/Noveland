from noveland.worlds.clock import (
    ClockTransition,
    WorldClockError,
    WorldClockState,
    WorldClockStateError,
    WorldClockStatus,
    WorldClockTimeError,
    WorldClockTransitionType,
    advance_clock,
    current_world_time_at,
    pause_clock,
    resume_clock,
    skip_clock,
)
from noveland.worlds.clock_service import WorldClockService, WorldClockView
from noveland.worlds.worldlines import (
    DEFAULT_WORLDLINE_ACTOR_REF,
    PRIMARY_WORLDLINE_KEY,
    PRIMARY_WORLDLINE_NAME,
    ensure_primary_worldline,
    primary_worldline_or_none,
    worldline_or_404,
)

PACKAGE_NAME = "worlds"

_AUTONOMOUS_EXPORTS = {
    "DailyLifePreviewResult",
    "LivingWorldAutonomyService",
    "OffscreenResolutionResult",
}

__all__ = [
    "PACKAGE_NAME",
    "ClockTransition",
    "DailyLifePreviewResult",
    "LivingWorldAutonomyService",
    "OffscreenResolutionResult",
    "WorldClockError",
    "WorldClockState",
    "WorldClockStateError",
    "WorldClockStatus",
    "WorldClockTimeError",
    "WorldClockTransitionType",
    "WorldClockService",
    "WorldClockView",
    "DEFAULT_WORLDLINE_ACTOR_REF",
    "PRIMARY_WORLDLINE_KEY",
    "PRIMARY_WORLDLINE_NAME",
    "advance_clock",
    "current_world_time_at",
    "ensure_primary_worldline",
    "pause_clock",
    "primary_worldline_or_none",
    "resume_clock",
    "skip_clock",
    "worldline_or_404",
]


def __getattr__(name: str) -> object:
    if name in _AUTONOMOUS_EXPORTS:
        from noveland.worlds import autonomous

        return getattr(autonomous, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
