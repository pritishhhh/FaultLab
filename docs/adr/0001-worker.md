# ADR 0001: Dedicated experiment worker

Accepted for the local prototype. Experiments execute in a separate process instead of FastAPI background tasks. A worker claims queued rows, refreshes a database lease while storing snapshots, and reconciles expired leases as failures. This makes API restarts independent of execution. Multiworker ownership still needs stronger fencing before production scaling.
