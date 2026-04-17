# World Clock and Scheduling

## Principle

World time is an internal kernel concern, not an external cron concern.

## Required world-time capabilities

- real-time continuous operation
- pause
- resume
- acceleration
- skip/jump
- replay foundation

## Scheduling model

- wall-clock drives runtime loops
- world clock maps wall-clock progression into world-time progression
- timetable, weekday, weekend, holiday, and scheduled agent behavior are resolved against world time
- manual narrative triggers are separate from world-time authority

## Rules

- no external scheduler becomes the source of truth for world time
- schedule rules must be world-scoped
- per-agent calendars must resolve against world time
- clock state changes are auditable

## Implemented baseline

- `noveland.worlds.clock` defines immutable clock state and pure transitions for pause, resume, advance, skip, and current-time projection.
- `world_clock_states` stores one current clock state row per world.
- `world_clock_transitions` stores append-only operational audit records for clock state changes.
- `noveland.worlds.clock_service` persists clock state changes and transition audit records.
- New worlds are initialized with a paused clock automatically.
- The backend exposes member-readable and admin-controlled clock HTTP endpoints under `/worlds/{world_id}/clock`.
- The web dashboard shows the selected world's clock and admin controls for pause, resume, advance, and skip.
- The runtime host can perform one finite tick: active running clocks are advanced, transition audit rows are written, `world.clock_advanced` events are appended, and event envelopes are broadcast to NATS.
- `wall_time_anchor` is present only while a clock is running; paused clocks keep a materialized `current_world_time`.
- `speed_multiplier` must be greater than zero; pause is represented by `status=paused`, not by setting speed to zero.

## v1 simplification

Advanced user-facing replay UI may be deferred, but clock state and recovery semantics may not be deferred.

The current baseline intentionally does not implement infinite runtime loops, external schedulers, calendar parsing, agent schedule execution, or clock-event emission from manual HTTP controls.
