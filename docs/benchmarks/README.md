# Benchmarking

Run `python docs/benchmarks/run.py --base-url http://localhost:8080 --service-id SERVICE_ID --output docs/benchmarks/results/local.json` after starting Compose and registering the demo gateway. The script runs baseline plus selected managed fault scenarios sequentially, waits for a report, and writes actual API results. Results are ignored by Git because they are host-specific. No performance numbers are fabricated or committed.
