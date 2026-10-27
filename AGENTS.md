# AstroFairy development

Independent project. Keep all project changes here; do not change sibling repositories.

| Topic | Authority / check |
|---|---|
| Architecture and trust boundary | [Architecture](docs/guides/architecture.md) |
| Protocol | `python -m astrofairy schema`; implementation under `skills/astrofairy/scripts/astrofairy/` |
| Work and asset lifecycle | [Operation](docs/guides/operation.md) |
| Design decisions | [Core](docs/adr/0001-small-workshop.md), [distribution](docs/adr/0002-portable-standard-skill.md) |
| Test and package checks | `python dev/check.py` |
| Tool versions | `requirements-dev.lock`; no duplicated tool pins |

Python 3.12+, standard-library runtime, private modules and explicit public exports.
Public prose and interfaces use neutral, professional task terminology.
Tests belong to their code owner; `governance.toml` declares their execution surfaces.
Keep protocol validation, invocation and event storage distinct. Task-specific policy belongs to assets.
Use typed interfaces, explicit UTF-8, parameterized SQL and argument-array subprocesses.
Never claim a model report is a tool observation. Checks bind task revision and immutable content.
Unknown execution results remain unknown; task closure does not discard late observations or feedback.
Learning updates assets through validation, not this file. Keep the skill entry and core within checked budgets.
Run checks before committing; never skip hooks. Commits use Conventional Commits; do not commit unless asked.
