# Media Assets Not Narrative Artifacts

## Status

Accepted

## Context

Narrative artifacts are prose/publication records. Image/audio/video/document bytes require lifecycle, object storage, checksums, jobs, lineage, and ACLs.

## Decision

Media must use `media_assets`, `media_objects`, `media_jobs`, and `media_references`. `narrative_artifacts` must not be used as binary media storage.

## Consequences

Media storage integrity and delivery remain centralized. Narrative records can reference media through explicit references without carrying bytes or storage paths.

## Non-goals

- Public reader media delivery.
- Replacing narrative publication workflows.
- Storing bytes/base64 in event or narrative payloads.

## Related files/tests

- `backend/packages/media/src/noveland/media/models.py`
- `backend/packages/narrative/src/noveland/narrative/models.py`
- `backend/tests/test_media_service.py`
- `backend/tests/test_api_media.py`
