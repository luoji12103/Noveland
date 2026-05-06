from __future__ import annotations

import uuid

from noveland.worlds.models import Worldline
from sqlalchemy import select
from sqlalchemy.orm import Session

PRIMARY_WORLDLINE_KEY = "primary"
PRIMARY_WORLDLINE_NAME = "Primary Worldline"
DEFAULT_WORLDLINE_ACTOR_REF = "system:runtime"


def ensure_primary_worldline(
    session: Session,
    world_id: uuid.UUID,
    *,
    actor_ref: str = DEFAULT_WORLDLINE_ACTOR_REF,
) -> Worldline:
    worldline = primary_worldline_or_none(session, world_id)
    if worldline is not None:
        return worldline
    worldline = Worldline(
        id=uuid.uuid4(),
        world_id=world_id,
        worldline_key=PRIMARY_WORLDLINE_KEY,
        name=PRIMARY_WORLDLINE_NAME,
        description="Default branch for pre-worldline and mainline world state.",
        parent_worldline_id=None,
        forked_from_snapshot_id=None,
        fork_event_sequence=None,
        status="active",
        created_by_actor_ref=actor_ref,
        metadata_json={"primary": True},
    )
    session.add(worldline)
    session.flush()
    return worldline


def primary_worldline_or_none(session: Session, world_id: uuid.UUID) -> Worldline | None:
    return session.scalars(
        select(Worldline)
        .where(Worldline.world_id == world_id, Worldline.parent_worldline_id.is_(None))
        .order_by(Worldline.created_at, Worldline.worldline_key)
        .limit(1),
    ).first()


def worldline_or_404(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID | None,
) -> Worldline:
    if worldline_id is None:
        return ensure_primary_worldline(session, world_id)
    worldline = session.get(Worldline, worldline_id)
    if worldline is None or worldline.world_id != world_id:
        raise ValueError("worldline not found")
    return worldline
