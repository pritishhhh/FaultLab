# Architecture

The control plane validates registrations and experiment configurations, writes immutable execution configuration to PostgreSQL, and exposes read APIs and WebSocket projections. The worker polls queued experiments, owns a lease, sends traffic through gateway → order → payment, applies faults through payment's internal authenticated endpoint, and stores metrics/events/reports. PostgreSQL is the source of truth. Redis is included for future message fanout but is not currently required for correctness.

Data model: `Service`, `Experiment`, `FaultConfiguration`, `MetricSnapshot`, `ExperimentEvent`, and `ExperimentReport`. `FaultConfiguration` has a unique experiment foreign key. Events have a unique `(experiment_id, sequence)` pair. The experiment starts only after explicit `/start` and configuration is never updated by the API afterward.

The API returns JSON errors as `{ "error": { "code": "...", "message": "..." } }`. Validation errors include `details`. Database errors return 503. WebSockets transmit state, event, and metric frames; clients deduplicate events by sequence and metrics by ID if needed. A fresh connection replays persisted events.

The demo services expose `/health` and `/ready`. `X-Request-ID` is forwarded at each hop and included in structured logs. Upstream timeouts are bounded at 0.8 and 1.2 seconds.
