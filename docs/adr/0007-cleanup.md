# ADR 0007: Retried cleanup and visible failure

Accepted. The worker removes the fault before recovery and retries removal three times on exception/cancellation. Lease reconciliation attempts cleanup after a worker crash. If cleanup still fails, `fault_active` and an error message expose required operator action. Automatic cleanup after host-wide outage is not guaranteed.
