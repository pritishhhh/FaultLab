# Deterministic resilience score

Let baseline p95 be `b`, fault p95 be `f`, fault error rate be `e_f`, and baseline error rate be `e_b`. Use `max(b, 1 ms)` for numeric stability.

- Availability component: `A = max(0, 1 - e_f)`.
- Latency component: `L = min(1, b / max(f, b))`.
- Error component: `E = max(0, 1 - e_f)`.
- Recovery component: `R = 1` if baseline has requests and at most 10% errors, recovery has requests, recovery p95 ≤ `max(1.5b, b + 30 ms)`, and recovery error rate ≤ `min(max(e_b + 0.05, 0.05), 0.10)`; otherwise `R = 0`.
- Score: `round(100 × (0.35A + 0.20L + 0.20E + 0.25R))`, clipped to `[0, 100]`.

An unhealthy baseline (no requests or more than 10% errors) receives score 0. The experiment worker fails such a run after baseline rather than applying a fault to an already unhealthy target.

Latency amplification is `f / max(b, 1 ms)`. Error amplification is `e_f / e_b` when baseline errors are nonzero; otherwise it is `null`, not infinity. Classifications are threshold observations and are not causal diagnoses. Recovery time in seconds is not yet measured as a first-class metric; `R` only indicates the recovery window endpoint met thresholds.
