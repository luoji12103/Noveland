## MODIFIED Requirements

### Requirement: Reader delivery enforces visibility
The system SHALL enforce media, object, reference, presentation, and narrative publication visibility before serving reader media.

#### Scenario: Reader media object delivery rejects active content types
- **Given** a reader-visible media asset has media objects attached to a published reader surface
- **When** an authorized reader requests its descriptor or object download
- **Then** reader delivery SHALL expose only objects whose MIME type is safe for the declared reader media kind: whitelisted image formats for images, whitelisted audio formats for audio, and whitelisted browser video container formats for video
- **And** objects with active document or scriptable content types such as `text/html`, `application/xhtml+xml`, or SVG SHALL be omitted from reader descriptors and SHALL NOT be downloadable through reader media routes
- **And** an asset with no safe reader-deliverable objects SHALL be omitted from list results and return a not-found response for detail and download requests.

#### Scenario: Reader playback does not substitute unresolved explicit presentation media
- **Given** a member-readable turn presentation names explicit image or audio media asset identifiers for reader playback
- **And** reader media descriptors omit those asset identifiers because the assets are unavailable, unsafe, hidden, missing references, or otherwise not reader-deliverable
- **When** Web playback or scene view resolves media for the turn
- **Then** the UI SHALL render the missing-media state for that media kind instead of falling back to unrelated turn-level or session-level referenced media
- **And** referenced media fallback MAY be used only when the presentation has no explicit media asset identifier for that media kind.
