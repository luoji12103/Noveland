from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from noveland.package_contracts import (
    PackageContractService,
    PackageContractValidationRequest,
    PackageContractValidationResult,
    PackageProviderConfigExport,
)
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
)
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/worlds/{world_id}/package-contracts",
    tags=["package-contracts"],
)


@router.post("/validate", response_model=PackageContractValidationResult)
def validate_package_contract(
    world_id: uuid.UUID,
    request: PackageContractValidationRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PackageContractValidationResult:
    return PackageContractService(db_session).validate_package_contract(world_id, request)


@router.get("/provider-config-export", response_model=PackageProviderConfigExport)
def export_provider_package_config(
    world_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    include_global: Annotated[bool, Query()] = True,
    include_hidden: Annotated[bool, Query()] = False,
) -> PackageProviderConfigExport:
    return PackageContractService(db_session).export_provider_configs(
        world_id,
        platform_admin=context.is_platform_admin,
        include_global=include_global,
        include_hidden=include_hidden,
    )
