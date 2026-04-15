# Testing Strategy

## Test layers

### Unit tests
Required for:
- world rules
- calendar logic
- auth checks
- observation shaping
- plugin validation

### Integration tests
Required for:
- API + DB interactions
- runtime + event store interactions
- summarizer trigger flow
- world-scoped isolation

### Replay/regression tests
Required for:
- snapshot restore
- event replay
- clock state transitions
- access control regressions

### Frontend tests
- component tests for complex logic
- Playwright for key user paths

## Feature rule

A feature is not complete if its critical behavior has no test coverage strategy.
