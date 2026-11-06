# AstroFairy development

Independent project. Keep all project changes here; do not change sibling repositories.
Before implementation, read [current status](STATUS.md) and [contributor guide](CONTRIBUTING.md).
Use this project's [GitHub Issues](https://github.com/Etoileint/AstroFairy/issues); reports need verification.
When using an authorized external development organization, load its original router/method packages
and follow the [scope rules](CONTRIBUTING.md#external-development-organization); keep all project records here.

| Topic | Authority / check |
|---|---|
| Developer entry and evidence | [Contributing](CONTRIBUTING.md), [status](STATUS.md), [evidence access](docs/development/evidence.md) |
| Architecture and trust boundary | [Architecture](docs/guides/architecture.md) |
| Protocol | `python -m astrofairy schema`; implementation under `skills/fairy/scripts/astrofairy/` |
| Work and asset lifecycle | [Operation](docs/guides/operation.md) |
| Historical reviews | [Review workspace](docs/reviews/README.md), [rounds](docs/reviews/INDEX.md); inventory/source checks: `python dev/check_review_preparation.py` (not a product-conformance check) |
| Repair lineage | [Earlier repairs and continuing observations](docs/repairs/README.md); use STATUS.md for current work; historical review stays bound to its frozen Git baseline |
| Completed optimization | [Implementation record](docs/optimization/2026-11-implementation/README.md); [final technical acceptance](docs/optimization/2026-11-acceptance/final-2026-11-03/README.md); historical returns stay immutable |
| Design decisions | [Core](docs/adr/0001-small-workshop.md), [distribution](docs/adr/0002-portable-standard-skill.md) |
| Test and package checks | `python dev/check.py` |
| Tool versions | `requirements-dev.lock`; no duplicated tool pins |

Python 3.12+, hash-locked JSON Schema runtime, private modules and explicit public exports.
Runtime pins: `pyproject.toml`; generated lock/diagnostics: `python dev/lock_runtime.py --check`.
Public prose and interfaces use neutral, professional task terminology.
Tests belong to their code owner; `governance.toml` declares their execution surfaces.
Keep protocol validation, invocation and event storage distinct. Task-specific policy belongs to assets.
Use typed interfaces, explicit UTF-8, parameterized SQL and argument-array subprocesses.
Never claim a model report is a tool observation. Checks bind task revision and immutable content.
Unknown execution results remain unknown; task closure does not discard late observations or feedback.
Development has no backward-compatibility burden. Replace obsolete contracts cleanly; do not add migrations,
fallbacks or dual paths for old stores/interfaces. Preserve frozen review evidence as history.
Learning updates assets through validation, not this file. Keep essential execution information in the skill
entry. Review core responsibilities and size metrics; do not enforce arbitrary byte or physical-line caps.
Run checks before committing; never skip hooks. Commits use Conventional Commits; do not commit unless asked.
