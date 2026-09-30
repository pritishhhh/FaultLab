# ADR 0003: Explicit phase transitions

Accepted. A map of legal transitions rejects invalid state changes. Terminal states are immutable. Every transition adds a sequenced event in the same database transaction. API calls never mutate execution configuration after creation.
