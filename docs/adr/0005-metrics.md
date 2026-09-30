# ADR 0005: Raw latency within bounded windows

Accepted. Each traffic window keeps per-request latency observations only until aggregation. Percentiles interpolate the sorted observations, not averages of averages. The database stores aggregate snapshots plus per-phase aggregate results in the report.
