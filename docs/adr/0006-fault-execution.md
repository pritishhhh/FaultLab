# ADR 0006: In-process managed demo faults

Accepted. Payment implements bounded delay, deterministic errors, timeout delay, unavailability response, and bounded CPU work. An authenticated internal endpoint controls only that managed process. No Docker socket, shell, arbitrary URL, or remote host control is exposed.
