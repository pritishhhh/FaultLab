# ADR 0009: Threshold-based recovery

Accepted. Recovery requires at least one request, p95 no more than `max(1.5 × baseline p95, baseline p95 + 30 ms)`, and error rate no more than `max(baseline error rate + 5 points, 5%)`. This detects a recovery window outcome, not the exact recovery instant.
