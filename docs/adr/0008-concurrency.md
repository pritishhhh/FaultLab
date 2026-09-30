# ADR 0008: One active experiment per service

Accepted as a policy. The API rejects a second start when another experiment for the service is active or queued. The current check and write are not protected by a service-scoped database lock; simultaneous requests across API replicas may race. Production deployment requires an atomic lock or partial unique index before scaling the API.
