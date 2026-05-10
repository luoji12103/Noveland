from __future__ import annotations

import uuid
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events.models import WorldEventModel
from noveland.media.catalog import MediaCatalogService, MediaCollectionService, MediaLineageService
from noveland.media.contracts import (
    MediaAssetCollectionCreate,
    MediaAssetCollectionItemCreate,
    MediaAssetCollectionItemUpdate,
    MediaAssetSearchFilters,
    MediaAssetTagCreate,
    MediaAssetTagFilter,
    MediaVisibility,
)
from noveland.media.errors import MediaValidationError
from noveland.media.models import (
    MediaAsset,
    MediaAssetCollection,
    MediaAssetCollectionItem,
    MediaAssetContext,
    MediaAssetInput,
    MediaAssetTag,
    MediaJob,
)
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_media_catalog_service_tags_collections_search_and_lineage() -> None:
    engine = _engine()
    world_id, primary_id, fork_id, agent_id, conversation_id, turn_id = _seed_graph(engine)
    visible_id = _seed_asset(
        engine,
        world_id,
        primary_id,
        visibility="world_member",
        title="Shy sprite",
        description="A classroom sprite",
    )
    private_id = _seed_asset(engine, world_id, primary_id, visibility="private", title="Secret")
    fork_id_asset = _seed_asset(engine, world_id, fork_id, visibility="world_member")

    with Session(engine) as session:
        catalog = MediaCatalogService(session)
        tag = catalog.create_tag(
            world_id,
            visible_id,
            MediaAssetTagCreate(
                world_id=world_id,
                worldline_id=primary_id,
                tag_type="Emotion",
                tag_key="Mood",
                tag_value="shy:soft",
                visibility=MediaVisibility.WORLD_MEMBER,
            ),
            actor_ref="user:test",
        )
        hidden_tag = catalog.create_tag(
            world_id,
            private_id,
            MediaAssetTagCreate(
                world_id=world_id,
                worldline_id=primary_id,
                tag_type="emotion",
                tag_key="mood",
                tag_value="secret",
                visibility=MediaVisibility.HIDDEN,
            ),
            actor_ref="user:test",
        )
        collection = MediaCollectionService(session).create_collection(
            MediaAssetCollectionCreate(
                world_id=world_id,
                worldline_id=primary_id,
                collection_kind="Sprite_Set",
                title="Sprite set",
                owner_agent_id=agent_id,
                visibility=MediaVisibility.WORLD_MEMBER,
            ),
            actor_ref="user:test",
        )
        item = MediaCollectionService(session).add_item(
            world_id,
            collection.id,
            MediaAssetCollectionItemCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_id=visible_id,
            ),
        )
        _seed_context(session, world_id, primary_id, visible_id, agent_id, conversation_id, turn_id)
        _seed_input(
            session,
            world_id,
            primary_id,
            output_asset_id=private_id,
            input_asset_id=visible_id,
        )
        session.commit()

    with Session(engine) as session:
        catalog = MediaCatalogService(session)
        result = catalog.search_assets(
            world_id,
            MediaAssetSearchFilters(
                worldline_id=primary_id,
                contains_text=" shy ",
                collection_id=collection.id,
                used_by_agent_id=agent_id,
                tags=(MediaAssetTagFilter.parse("emotion:mood:shy:soft"),),
            ),
            member_visible_only=True,
        )
        hidden_result = catalog.search_assets(
            world_id,
            MediaAssetSearchFilters(
                worldline_id=primary_id,
                tags=(MediaAssetTagFilter.parse("emotion:mood:secret"),),
            ),
            member_visible_only=True,
        )
        refs = MediaLineageService(session).references(
            world_id,
            visible_id,
            member_visible_only=True,
        )
        lineage = MediaLineageService(session).lineage(
            world_id,
            visible_id,
            member_visible_only=True,
        )

        assert tag.tag_type == "emotion"
        assert tag.tag_key == "mood"
        assert tag.tag_value == "shy:soft"
        assert hidden_tag.visibility == MediaVisibility.HIDDEN
        assert item.asset_id == visible_id
        assert [asset.id for asset in result.assets] == [visible_id]
        assert hidden_result.assets == []
        assert refs.tag_count == 1
        assert refs.collection_count == 1
        assert refs.input_count == 0
        assert lineage.outputs == []

        with pytest.raises(MediaValidationError, match="tag asset must belong"):
            catalog.create_tag(
                world_id,
                fork_id_asset,
                MediaAssetTagCreate(
                    world_id=world_id,
                    worldline_id=primary_id,
                    tag_type="scene",
                    tag_key="place",
                    tag_value="classroom",
                ),
                actor_ref="user:test",
            )


def test_media_collection_service_rejects_cross_worldline_and_deleted_assets() -> None:
    engine = _engine()
    world_id, primary_id, fork_id, _agent_id, _conversation_id, _turn_id = _seed_graph(engine)
    visible_id = _seed_asset(engine, world_id, primary_id, visibility="world_member")
    deleted_id = _seed_asset(
        engine,
        world_id,
        primary_id,
        visibility="world_member",
        status="deleted",
    )
    fork_id_asset = _seed_asset(engine, world_id, fork_id, visibility="world_member")

    with Session(engine) as session:
        service = MediaCollectionService(session)
        collection = service.create_collection(
            MediaAssetCollectionCreate(
                world_id=world_id,
                worldline_id=primary_id,
                collection_kind="reference_set",
                title="References",
            ),
            actor_ref="user:test",
        )
        item = service.add_item(
            world_id,
            collection.id,
            MediaAssetCollectionItemCreate(
                world_id=world_id,
                worldline_id=primary_id,
                asset_id=visible_id,
            ),
        )
        updated = service.update_item(
            world_id,
            collection.id,
            item.id,
            item_update=MediaAssetCollectionItemUpdate(display_order=4),
        )
        assert updated.display_order == 4

        with pytest.raises(MediaValidationError, match="asset must match collection worldline"):
            service.add_item(
                world_id,
                collection.id,
                MediaAssetCollectionItemCreate(
                    world_id=world_id,
                    worldline_id=primary_id,
                    asset_id=fork_id_asset,
                ),
            )
        with pytest.raises(Exception, match="media asset not found"):
            service.add_item(
                world_id,
                collection.id,
                MediaAssetCollectionItemCreate(
                    world_id=world_id,
                    worldline_id=primary_id,
                    asset_id=deleted_id,
                ),
            )

def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    return engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Agent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaAssetContext.__table__),
        cast(Table, MediaAssetInput.__table__),
        cast(Table, MediaAssetTag.__table__),
        cast(Table, MediaAssetCollection.__table__),
        cast(Table, MediaAssetCollectionItem.__table__),
    ):
        table.create(engine)


def _seed_graph(
    engine: Engine,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="Test"))
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        session.flush()
        primary = ensure_primary_worldline(session, world_id)
        fork = Worldline(
            world_id=world_id,
            worldline_key=f"fork-{uuid.uuid4().hex[:8]}",
            name="Fork",
            parent_worldline_id=primary.id,
            status="active",
            created_by_actor_ref="test",
            metadata_json={},
        )
        session.add(fork)
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="agent",
                display_name="Agent",
                kind="role_agent",
            )
        )
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=primary.id,
                session_key="session-1",
                title="Session",
                scope_type="world",
                mode="manual_chain",
                status="draft",
                objective="",
                opening_prompt="",
                max_turns=3,
                next_turn_index=1,
                policy_config={},
                writer_config={},
                memory_config={},
            )
        )
        session.add(
            ConversationTurn(
                id=turn_id,
                session_id=conversation_id,
                turn_index=0,
                speaker_kind="operator",
                input_text="hi",
                output_text="hello",
                status="succeeded",
            )
        )
        session.commit()
        return world_id, primary.id, fork.id, agent_id, conversation_id, turn_id


def _seed_asset(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    visibility: str,
    status: str = "registered",
    title: str | None = None,
    description: str | None = None,
) -> uuid.UUID:
    asset_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="reference_image",
                source_kind="manual_upload",
                status=status,
                visibility=visibility,
                title=title,
                description=description,
                created_by_actor_ref="test",
                metadata_json={"secret": "not searchable"},
            )
        )
        session.commit()
    return asset_id


def _seed_context(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    asset_id: uuid.UUID,
    agent_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
) -> None:
    session.add(
        MediaAssetContext(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            asset_id=asset_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            agent_id=agent_id,
            context_role="attachment",
            metadata_json={},
        )
    )


def _seed_input(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    output_asset_id: uuid.UUID,
    input_asset_id: uuid.UUID,
) -> None:
    session.add(
        MediaAssetInput(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            output_asset_id=output_asset_id,
            input_asset_id=input_asset_id,
            input_role="reference",
            display_order=0,
            metadata_json={},
        )
    )
