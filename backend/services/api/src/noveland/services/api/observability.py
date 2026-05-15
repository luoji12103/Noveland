from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from noveland.auth import AuthenticatedSubject
from noveland.observability import IncidentDiagnosticsService, IncidentSummary
from noveland.services.api.dependencies import get_db_session, get_platform_admin_subject
from sqlalchemy.orm import Session

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/incidents/summary", response_model=IncidentSummary)
def get_incident_summary(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    world_id: Annotated[uuid.UUID | None, Query()] = None,
    retention_days: Annotated[int, Query(ge=1, le=3650)] = 30,
    evidence_limit_per_component: Annotated[int, Query(ge=1, le=20)] = 5,
) -> IncidentSummary:
    del subject
    return IncidentDiagnosticsService(db_session).summary(
        world_id=world_id,
        retention_days=retention_days,
        evidence_limit_per_component=evidence_limit_per_component,
    )
