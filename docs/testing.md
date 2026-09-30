# Testing and failure matrix

The checked-in tests cover raw percentile interpolation, empty windows, 429 and timeout accounting, score stability with zero baseline errors, legal/illegal state transitions, API validation and gating, and frontend fault-form validation. A real-process integration test starts all three demo HTTP services, the API, and the worker; it verifies request-ID propagation, the latency experiment lifecycle, report, and event order. These tests passed locally. Docker-specific and cloud-specific cases remain unrun.

The following reproducible checks require a running Compose stack. For each test, create a short experiment through the UI and inspect phase, event sequence, metrics, and report. Use a fresh registered gateway and `docker compose logs` for correlated request IDs.

| Cases | Procedure | Expected |
|---|---|
| Healthy target, normal lifecycle | Run latency fault at 10 rps | Completed; ordered events and three phase windows |
| Target unavailable before/during phases | Stop gateway/payment before or during a phase | Bounded failures; no hanging requests; no false recovery |
| Fault activation/cleanup unavailable | Stop payment near phase transition | Failed or cleanup-required error, not silent success |
| Cancel baseline/fault/recovery | Cancel from detail page | Terminal CANCELLED; fault removed when reachable |
| Worker crash | Restart worker during a phase; wait 15+ sec | Lease expiry, FAILED, cleanup attempt |
| Backend restart | Restart backend | Persisted experiment and WebSocket reconnection |
| Redis disconnect | Stop/restart Redis | API and worker retain PostgreSQL state |
| PostgreSQL disconnect | Stop/restart PostgreSQL | API 503 during outage, persisted state after recovery |
| Duplicate/malformed input | Repeat start/cancel, malformed fault/duration | 409 or 422 |
| Excess traffic/unregistered target | Submit >50 rps or unknown ID/URL | 422 or 404; no arbitrary target |
| HTTP 429/500, timeout, all failures | Adjust demo response or run fault | Counted as failure; report remains numeric |
| Concurrent experiments | Start two for same service | Second 409 when first is active; see ADR limitation |

Additional requested matrix cases (late snapshots, slow queries, duplicate events, stale Redis data, Docker startup races, and cloud task replacement) still need automated integration coverage. This table is a test plan, not a claim that those cases passed.
