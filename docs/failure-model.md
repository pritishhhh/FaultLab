# Fault and safety model

All automated faults are implemented inside the registered payment service. Its internal control endpoint requires `X-FaultLab-Token`. The control plane never accepts a target URL. The demo Docker network is internal and no demo port is published. These are useful local boundaries, not substitutes for production auth, network policy, or secret management.

Failure modes not injected by the API can be explored manually in a dedicated local Compose stack: `docker compose stop payment`, `docker compose restart worker`, `docker compose restart backend`, `docker compose stop redis`, `docker compose stop postgres`, followed by corresponding `start` commands. Observe state through `/api/experiments/{id}` and persisted events. Stopping the database can make the API return 503; restarting it should restore reads. Such procedures were not run in the authoring environment.

Clean-up failure is operator visible through `Experiment.error` and `fault_active`. Do not run a second fault against the same demo service until the managed fault is confirmed removed.
