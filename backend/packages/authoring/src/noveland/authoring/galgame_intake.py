from __future__ import annotations

import hashlib
import mimetypes
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from noveland.authoring.contracts import (
    AuthoringImportRunCreate,
    AuthoringImportRunKind,
    AuthoringSourceAssetCreate,
    AuthoringSourceAssetKind,
    AuthoringSourceBatchCreate,
    AuthoringSourceFragmentCreate,
    AuthoringSourceFragmentKind,
    AuthoringSourceVisibility,
    GalgameSourceIntakeApplyRequest,
    GalgameSourceIntakeApplyResult,
    GalgameSourceIntakeAssetRole,
    GalgameSourceIntakeFilePreview,
    GalgameSourceIntakeFileStatus,
    GalgameSourceIntakePreviewRequest,
    GalgameSourceIntakePreviewResult,
)
from noveland.authoring.service import AuthoringService, AuthoringValidationError
from noveland.media.contracts import (
    MediaAssetKind,
    MediaAssetRole,
    MediaAssetUploadRequest,
    MediaSourceKind,
    MediaVisibility,
)
from noveland.media.service import MediaService
from noveland.media.storage import MediaObjectStorage
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy.orm import Session

_TEXT_EXTS = {".txt", ".ks", ".csv", ".json", ".yaml", ".yml", ".md", ".script"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
_AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aac", ".webm"}
_DANGEROUS_EXTS = {
    ".7z",
    ".arc",
    ".bin",
    ".dat",
    ".dll",
    ".exe",
    ".iso",
    ".pak",
    ".rar",
    ".xp3",
    ".zip",
}
_TEXT_FRAGMENT_LINE_COUNT = 80


@dataclass(frozen=True, slots=True)
class _DiscoveredFile:
    path: Path
    source_ref: str
    file_name: str
    role: GalgameSourceIntakeAssetRole
    source_asset_kind: AuthoringSourceAssetKind
    media_asset_kind: MediaAssetKind | None
    media_asset_role: MediaAssetRole | None
    mime_type: str | None
    size_bytes: int
    fragment_count: int
    status: GalgameSourceIntakeFileStatus
    reason: str | None = None


class GalgameSourceIntakeService:
    def __init__(
        self,
        session: Session,
        storage: MediaObjectStorage | None = None,
    ) -> None:
        self._session = session
        self._storage = storage

    def preview(
        self,
        request: GalgameSourceIntakePreviewRequest,
    ) -> GalgameSourceIntakePreviewResult:
        worldline_id = worldline_or_404(
            self._session,
            request.world_id,
            request.worldline_id,
        ).id
        root = _safe_source_root(request.source_directory)
        discovered = _discover_files(root, request)
        return _preview_result(
            request,
            worldline_id=worldline_id,
            root=root,
            discovered=discovered,
        )

    def apply(
        self,
        request: GalgameSourceIntakeApplyRequest,
        *,
        actor_ref: str,
    ) -> GalgameSourceIntakeApplyResult:
        if self._storage is None:
            raise AuthoringValidationError("galgame source intake apply requires media storage")
        preview = self.preview(request)
        if preview.accepted_count == 0:
            raise AuthoringValidationError("galgame source intake found no accepted files")
        root = _safe_source_root(request.source_directory)
        discovered = _discover_files(root, request)
        authoring = AuthoringService(self._session)
        batch = authoring.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=request.world_id,
                worldline_id=request.worldline_id,
                batch_key=request.batch_key,
                display_name=request.display_name,
                description=request.description,
                source_kind=AuthoringSourceAssetKind.OTHER,
                visibility=AuthoringSourceVisibility.PRIVATE,
                metadata_json={
                    "source_type": "already_unpacked_galgame",
                    "root_label": preview.root_label,
                    "file_count": preview.accepted_count,
                    "provider_execution": False,
                    "canon_mutation": False,
                },
            ),
            actor_ref=actor_ref,
        )
        run = authoring.create_import_run(
            AuthoringImportRunCreate(
                world_id=request.world_id,
                worldline_id=request.worldline_id,
                source_batch_id=batch.id,
                run_kind=AuthoringImportRunKind.PREVIEW,
                summary_json={
                    "intake_kind": "galgame_source_directory",
                    "root_label": preview.root_label,
                    "accepted_count": preview.accepted_count,
                    "rejected_count": preview.rejected_count,
                    "media_file_count": preview.media_file_count,
                    "text_file_count": preview.text_file_count,
                    "fragment_count": preview.fragment_count,
                    "provider_execution": False,
                    "canon_mutation": False,
                },
            ),
            actor_ref=actor_ref,
        )
        source_assets = []
        source_fragments = []
        media_asset_ids: list[uuid.UUID] = []
        sequence = 0
        for item in discovered:
            if item.status != GalgameSourceIntakeFileStatus.ACCEPTED:
                continue
            media_asset_id = None
            if item.media_asset_kind is not None and item.media_asset_role is not None:
                upload = MediaService(self._session, self._storage).upload_asset(
                    MediaAssetUploadRequest(
                        world_id=request.world_id,
                        worldline_id=request.worldline_id,
                        asset_kind=item.media_asset_kind,
                        asset_role=item.media_asset_role,
                        source_kind=MediaSourceKind.IMPORTED_ORIGINAL,
                        visibility=MediaVisibility.PRIVATE,
                        title=item.file_name,
                        metadata={
                            "source_type": "already_unpacked_galgame",
                            "source_ref": item.source_ref,
                            "asset_role": item.role.value,
                            "generation_reference_candidate": item.media_asset_role
                            in {
                                MediaAssetRole.REFERENCE_IMAGE,
                                MediaAssetRole.CHARACTER_SPRITE,
                                MediaAssetRole.CHARACTER_EXPRESSION,
                                MediaAssetRole.SCENE_BACKGROUND,
                                MediaAssetRole.EVENT_CG,
                            },
                        },
                    ),
                    data=item.path.read_bytes(),
                    filename=item.file_name,
                    mime_type=item.mime_type or "application/octet-stream",
                    actor_ref=actor_ref,
                )
                media_asset_id = upload.asset.id
                media_asset_ids.append(upload.asset.id)
            source_asset = authoring.add_source_asset(
                AuthoringSourceAssetCreate(
                    world_id=request.world_id,
                    worldline_id=request.worldline_id,
                    batch_id=batch.id,
                    media_asset_id=media_asset_id,
                    source_asset_kind=item.source_asset_kind,
                    source_label=item.file_name,
                    source_ref=item.source_ref,
                    metadata_json={
                        "source_type": "already_unpacked_galgame",
                        "asset_role": item.role.value,
                        "mime_type": item.mime_type,
                        "size_bytes": item.size_bytes,
                        "extension": item.path.suffix.lower(),
                    },
                )
            )
            source_assets.append(source_asset)
            if item.source_asset_kind in {
                AuthoringSourceAssetKind.SCRIPT,
                AuthoringSourceAssetKind.CHARACTER_SHEET,
                AuthoringSourceAssetKind.DOCUMENT,
            }:
                for fragment_index, excerpt in enumerate(
                    _text_fragments(item.path, request.max_text_fragment_chars),
                ):
                    fragment = authoring.add_source_fragment(
                        AuthoringSourceFragmentCreate(
                            world_id=request.world_id,
                            worldline_id=request.worldline_id,
                            source_asset_id=source_asset.id,
                            fragment_key=f"{item.source_ref}-{fragment_index + 1}",
                            fragment_kind=_fragment_kind_for_role(item.role),
                            sequence=sequence,
                            excerpt_text=excerpt,
                            locator_json={
                                "source_ref": item.source_ref,
                                "fragment_index": fragment_index,
                            },
                            metadata_json={
                                "source_type": "already_unpacked_galgame",
                                "asset_role": item.role.value,
                            },
                        )
                    )
                    source_fragments.append(fragment)
                    sequence += 1
        return GalgameSourceIntakeApplyResult(
            preview=preview,
            batch=batch,
            run=run,
            source_assets=tuple(source_assets),
            source_fragments=tuple(source_fragments),
            media_asset_ids=tuple(media_asset_ids),
        )


def _safe_source_root(raw_path: str) -> Path:
    root = Path(raw_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise AuthoringValidationError("source_directory must be an existing directory")
    if root == root.parent:
        raise AuthoringValidationError("source_directory must not be filesystem root")
    return root


def _discover_files(
    root: Path,
    request: GalgameSourceIntakePreviewRequest,
) -> list[_DiscoveredFile]:
    files = [path for path in sorted(root.rglob("*")) if path.is_file()]
    if len(files) > request.max_files:
        raise AuthoringValidationError("source_directory contains too many files for one intake")
    return [_classify_file(root, path, request.max_text_fragment_chars) for path in files]


def _classify_file(
    root: Path,
    path: Path,
    max_text_fragment_chars: int,
) -> _DiscoveredFile:
    source_ref = _source_ref(root, path)
    file_name = path.name
    suffix = path.suffix.lower()
    try:
        size_bytes = path.stat().st_size
    except OSError as exc:
        raise AuthoringValidationError("source file is not readable") from exc
    if _is_hidden_or_unsafe(path, root):
        return _rejected(path, source_ref, file_name, size_bytes, "hidden or unsafe filename")
    if suffix in _DANGEROUS_EXTS:
        return _rejected(
            path,
            source_ref,
            file_name,
            size_bytes,
            "archive, executable, or packed container is not accepted",
        )
    role = _role_from_source_ref(source_ref, suffix)
    source_asset_kind = _source_asset_kind(role, suffix)
    media_kind, media_role = _media_shape(role, suffix)
    mime_type = _mime_type(path, media_kind)
    fragment_count = 0
    if suffix in _TEXT_EXTS:
        fragment_count = len(_text_fragments(path, max_text_fragment_chars))
    if media_kind is None and suffix not in _TEXT_EXTS:
        return _rejected(path, source_ref, file_name, size_bytes, "unsupported file extension")
    return _DiscoveredFile(
        path=path,
        source_ref=source_ref,
        file_name=file_name,
        role=role,
        source_asset_kind=source_asset_kind,
        media_asset_kind=media_kind,
        media_asset_role=media_role,
        mime_type=mime_type,
        size_bytes=size_bytes,
        fragment_count=fragment_count,
        status=GalgameSourceIntakeFileStatus.ACCEPTED,
    )


def _rejected(
    path: Path,
    source_ref: str,
    file_name: str,
    size_bytes: int,
    reason: str,
) -> _DiscoveredFile:
    return _DiscoveredFile(
        path=path,
        source_ref=source_ref,
        file_name=file_name,
        role=GalgameSourceIntakeAssetRole.OTHER,
        source_asset_kind=AuthoringSourceAssetKind.OTHER,
        media_asset_kind=None,
        media_asset_role=None,
        mime_type=None,
        size_bytes=size_bytes,
        fragment_count=0,
        status=GalgameSourceIntakeFileStatus.REJECTED,
        reason=reason,
    )


def _preview_result(
    request: GalgameSourceIntakePreviewRequest,
    *,
    worldline_id: uuid.UUID,
    root: Path,
    discovered: list[_DiscoveredFile],
) -> GalgameSourceIntakePreviewResult:
    file_previews = tuple(
        GalgameSourceIntakeFilePreview(
            source_ref=item.source_ref,
            file_name=item.file_name,
            status=item.status,
            asset_role=item.role,
            source_asset_kind=item.source_asset_kind,
            media_asset_kind=None if item.media_asset_kind is None else item.media_asset_kind.value,
            media_asset_role=None if item.media_asset_role is None else item.media_asset_role.value,
            mime_type=item.mime_type,
            size_bytes=item.size_bytes,
            fragment_count=item.fragment_count,
            reason=item.reason,
        )
        for item in discovered
    )
    accepted = [
        item for item in discovered if item.status == GalgameSourceIntakeFileStatus.ACCEPTED
    ]
    rejected = [
        item for item in discovered if item.status == GalgameSourceIntakeFileStatus.REJECTED
    ]
    skipped = [item for item in discovered if item.status == GalgameSourceIntakeFileStatus.SKIPPED]
    return GalgameSourceIntakePreviewResult(
        world_id=request.world_id,
        worldline_id=worldline_id,
        batch_key=request.batch_key,
        display_name=request.display_name,
        root_label=root.name,
        accepted_count=len(accepted),
        rejected_count=len(rejected),
        skipped_count=len(skipped),
        media_file_count=sum(1 for item in accepted if item.media_asset_kind is not None),
        text_file_count=sum(1 for item in accepted if item.path.suffix.lower() in _TEXT_EXTS),
        fragment_count=sum(item.fragment_count for item in accepted),
        files=file_previews,
    )


def _source_ref(root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:16]
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", path.stem).strip("-._").lower()[:50]
    if not stem:
        stem = "source"
    return f"{stem}-{digest}"


def _is_hidden_or_unsafe(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return path.is_symlink() or any(
        part.startswith(".") or part in {"", ".", ".."} for part in relative.parts
    )


def _role_from_source_ref(source_ref: str, suffix: str) -> GalgameSourceIntakeAssetRole:
    lowered = source_ref.lower()
    if suffix in _AUDIO_EXTS:
        if any(token in lowered for token in ("bgm", "music")):
            return GalgameSourceIntakeAssetRole.BGM
        if any(token in lowered for token in ("se", "sfx", "sound")):
            return GalgameSourceIntakeAssetRole.SOUND_EFFECT
        return GalgameSourceIntakeAssetRole.VOICE_REFERENCE
    if suffix in _TEXT_EXTS:
        if any(token in lowered for token in ("profile", "character", "chara")):
            return GalgameSourceIntakeAssetRole.CHARACTER_PROFILE
        if any(token in lowered for token in ("route", "choice")):
            return GalgameSourceIntakeAssetRole.ROUTE_CHOICE
        return GalgameSourceIntakeAssetRole.SCRIPT_DIALOGUE
    if any(token in lowered for token in ("background", "bg", "scene")):
        return GalgameSourceIntakeAssetRole.BACKGROUND
    if any(token in lowered for token in ("cg", "event")):
        return GalgameSourceIntakeAssetRole.CG
    if any(token in lowered for token in ("expression", "face", "variant", "happy", "sad")):
        return GalgameSourceIntakeAssetRole.EXPRESSION_VARIANT
    if suffix in _IMAGE_EXTS:
        return GalgameSourceIntakeAssetRole.CHARACTER_SPRITE
    return GalgameSourceIntakeAssetRole.OTHER


def _source_asset_kind(
    role: GalgameSourceIntakeAssetRole,
    suffix: str,
) -> AuthoringSourceAssetKind:
    if suffix in _IMAGE_EXTS:
        return AuthoringSourceAssetKind.IMAGE
    if suffix in _AUDIO_EXTS:
        return AuthoringSourceAssetKind.AUDIO
    if role == GalgameSourceIntakeAssetRole.SCRIPT_DIALOGUE:
        return AuthoringSourceAssetKind.SCRIPT
    if role == GalgameSourceIntakeAssetRole.CHARACTER_PROFILE:
        return AuthoringSourceAssetKind.CHARACTER_SHEET
    if role == GalgameSourceIntakeAssetRole.ROUTE_CHOICE:
        return AuthoringSourceAssetKind.SCRIPT
    if suffix in _TEXT_EXTS:
        return AuthoringSourceAssetKind.DOCUMENT
    return AuthoringSourceAssetKind.OTHER


def _media_shape(
    role: GalgameSourceIntakeAssetRole,
    suffix: str,
) -> tuple[MediaAssetKind | None, MediaAssetRole | None]:
    if suffix in _IMAGE_EXTS:
        return (
            MediaAssetKind.IMAGE,
            {
                GalgameSourceIntakeAssetRole.BACKGROUND: MediaAssetRole.SCENE_BACKGROUND,
                GalgameSourceIntakeAssetRole.CG: MediaAssetRole.EVENT_CG,
                GalgameSourceIntakeAssetRole.EXPRESSION_VARIANT: (
                    MediaAssetRole.CHARACTER_EXPRESSION
                ),
                GalgameSourceIntakeAssetRole.CHARACTER_SPRITE: MediaAssetRole.CHARACTER_SPRITE,
            }.get(role, MediaAssetRole.REFERENCE_IMAGE),
        )
    if suffix in _AUDIO_EXTS:
        return (
            MediaAssetKind.AUDIO,
            {
                GalgameSourceIntakeAssetRole.VOICE_REFERENCE: MediaAssetRole.VOICE_SAMPLE,
                GalgameSourceIntakeAssetRole.BGM: MediaAssetRole.VOICE_FILE,
                GalgameSourceIntakeAssetRole.SOUND_EFFECT: MediaAssetRole.VOICE_FILE,
            }.get(role, MediaAssetRole.VOICE_FILE),
        )
    return None, None


def _fragment_kind_for_role(
    role: GalgameSourceIntakeAssetRole,
) -> AuthoringSourceFragmentKind:
    if role == GalgameSourceIntakeAssetRole.SCRIPT_DIALOGUE:
        return AuthoringSourceFragmentKind.DIALOGUE
    if role == GalgameSourceIntakeAssetRole.CHARACTER_PROFILE:
        return AuthoringSourceFragmentKind.CHARACTER
    if role == GalgameSourceIntakeAssetRole.ROUTE_CHOICE:
        return AuthoringSourceFragmentKind.SCENE
    return AuthoringSourceFragmentKind.OTHER


def _mime_type(path: Path, media_kind: MediaAssetKind | None) -> str | None:
    if media_kind is None:
        return None
    guessed, _encoding = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    if media_kind == MediaAssetKind.IMAGE:
        return "image/png"
    return "audio/wav"


def _text_fragments(path: Path, max_chars: int) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines:
        return []
    fragments: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        addition_len = len(line) + 1
        if current and (
            len(current) >= _TEXT_FRAGMENT_LINE_COUNT
            or current_len + addition_len > max_chars
        ):
            fragments.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += addition_len
    if current:
        fragments.append("\n".join(current))
    return fragments
