# ADR 0001: Small control protocol, extensible workshop

Status: adopted for the first implementation.

The standard-library-only runtime decision below is superseded by
[ADR-0005](0005-declared-tool-contracts.md); the small protocol and workshop boundary remain.

## Decision

Use one Python package, a standard-library SQLite runtime and a conversation-host skill.
Keep admission, invocation and durable recording distinct, connected by explicit contracts.
Use the host's existing model rather than introduce a provider SDK, account setup or a service.
Treat learning maintenance as ordinary work that changes assets; do not append experience to AGENTS.md.

## Organization

Borrow single-source definitions, checked invariants, owner-local tests, progressive skill disclosure and
separate guides/decisions/reports from AstroProject. Apply them at single-package scale.
Keep this repository independent. No package dependency, repository registration, synchronization,
shared issue tracker or machine-specific path binds it to the source project.

Use `governance.toml` for test surfaces and growth budgets, the command parser for protocol fields,
the version module for package version and the development lock for tool versions.
Documentation explains decisions and limitations; it does not define a competing executable schema.

## Consequences

The first version is runnable without a model API key and can package a self-contained skill.
Real semantic quality and host cooperation remain explicit dependencies. Future hosts can use the same
protocol; new capability adapters and workflow assets do not require new kernel responsibilities.
Core changes need a demonstrated missing responsibility and review of replacement or consolidation.
