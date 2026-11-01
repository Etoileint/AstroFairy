# AstroFairy development

Independent project. Keep all project changes here; do not change sibling repositories.

| Topic | Authority / check |
|---|---|
| Architecture and trust boundary | [Architecture](docs/guides/architecture.md) |
| Protocol | `python -m astrofairy schema`; implementation under `skills/astrofairy/scripts/astrofairy/` |
| Work and asset lifecycle | [Operation](docs/guides/operation.md) |
| Overall review | [Review workspace](docs/reviews/README.md), [rounds](docs/reviews/INDEX.md); inventory/source checks: `python dev/check_review_preparation.py` (not a product-conformance check) |
| Repairs | [Live repair status](docs/repairs/README.md); historical review stays bound to its frozen Git baseline |
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
Learning updates assets through validation, not this file. Keep the skill entry and core within checked budgets.
Run checks before committing; never skip hooks. Commits use Conventional Commits; do not commit unless asked.
