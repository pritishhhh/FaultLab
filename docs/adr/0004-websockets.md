# ADR 0004: WebSockets project persisted state

Accepted. The server polls PostgreSQL and streams state, new events, and latest metrics. Reconnection replays events. This is simple and preserves correctness if connections drop, at the cost of query overhead and one-second latency.
