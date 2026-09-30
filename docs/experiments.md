# Experiment lifecycle

`CREATED → BASELINE → FAULT_INJECTION → RECOVERY → COMPLETED`; `FAILED` and `CANCELLED` are terminal exceptions. The worker verifies gateway readiness, then generates traffic in bounded one-second windows. It activates a managed payment fault before the fault period and removes it before recovery. Fault removal is retried three times on exceptions or cancellation. Each phase transition and completion writes an event. A report is created only after all three windows finish.

Cancellation is polled between traffic scheduling iterations. In-flight requests finish under bounded client timeouts. A cancelled queued experiment becomes `CANCELLED` immediately; an active one is finalized by its worker.
