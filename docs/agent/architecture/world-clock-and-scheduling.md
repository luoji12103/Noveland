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

## v1 simplification

Advanced user-facing replay UI may be deferred, but clock state and recovery semantics may not be deferred.
