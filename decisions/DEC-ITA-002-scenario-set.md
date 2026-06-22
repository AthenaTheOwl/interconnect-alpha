# DEC-ITA-002: Scenario Set

Status: accepted for v0.1.

## Decision

Declare v0.1 capacity-price cases in `data/scenarios.yaml` and mark exactly one
canonical scenario. The current canonical case is `base-case`.

## Rationale

The no-arg validation command needs a deterministic scenario to validate. A
small YAML file is enough for the first artifact and can expand when the RPM
history ingest lands.

## Consequences

- `python -m interconnect_alpha validate` does not require `--scenario`.
- Additional scenarios can be added without changing the CLI contract.

