# Benchmarking

Run `python docs/benchmarks/run.py --base-url http://localhost:8080 --service-id SERVICE_ID --output docs/benchmarks/results/local.json` after starting Compose and registering the demo gateway. Or run `python docs/benchmarks/run_local.py --output docs/benchmarks/results/local.json --window-seconds 10 --rps 2` to start disposable loopback services and a SQLite database automatically. The script runs baseline plus seven managed fault scenarios sequentially, waits for a report, and writes actual API results. Results are host-specific measurements, not expected-performance targets.

## Measured local run, 2026-10-01

The committed [raw result](results/local-validated-2026-10-01.json) came from Windows 11 loopback processes, SQLite, 2 configured requests/sec, and 10-second baseline/fault/recovery windows. All seven experiments completed and recorded zero client timeouts. Values below are read from that JSON; p95 values are milliseconds. This is a smoke benchmark with only 16–20 requests per phase, so percentiles are noisy.

| Scenario | Baseline p95 | Fault p95 | Fault error rate | Recovery p95 | Score |
|---|---:|---:|---:|---:|---:|
| 100 ms latency | 1240.50 | 893.30 | 0% | 781.80 | 100 |
| 300 ms latency | 800.90 | 1390.75 | 0% | 768.35 | 92 |
| 500 ms latency | 797.80 | 1148.40 | 0% | 1047.75 | 94 |
| 5% errors | 859.80 | 813.60 | 5% | 797.80 | 97 |
| 10% errors | 1156.00 | 1236.40 | 5.56% | 1235.00 | 96 |
| Dependency unavailable | 1078.00 | 1062.05 | 100% | 1047.75 | 45 |
| CPU pressure | 1094.00 | 1303.25 | 0% | 892.55 | 97 |

The 100 ms case did not show latency amplification, and 500 ms measured less amplification than 300 ms. Baseline latency varied substantially between sequential runs. The 10% error fault produced one observed HTTP 503 among 18 fault-window requests, so its measured 5.56% rate is sampling variation. These results show the experiment pipeline and outage detection, but they are not reliable service capacity estimates. Rerun on a stable Linux/Docker host with longer windows before drawing performance conclusions.
