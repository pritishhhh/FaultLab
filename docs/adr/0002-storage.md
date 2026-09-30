# ADR 0002: PostgreSQL is authoritative

Accepted. PostgreSQL stores configuration, phase, events, snapshots, and reports. Redis does not hold correctness-critical data. The current implementation does not yet use Redis fanout; therefore a Redis outage should not change persisted state, but reconnect behavior remains untested.
