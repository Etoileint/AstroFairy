# Contributing to AstroFairy

Read [AGENTS.md](AGENTS.md), then [current development status](STATUS.md). This guide applies to human
contributors and coding agents. The [conceptual walkthrough](docs/guides/understanding-astrofairy.md)
explains the product in Chinese; [README.zh-CN.md](README.zh-CN.md#开发) contains the development commands.

## Prepare a checkout

Use a normal Git clone with full history. Historical-baseline tests read older Git objects; a shallow
clone or GitHub source ZIP alone is insufficient for that part of the check suite.

```sh
git clone https://github.com/Etoileint/AstroFairy.git
cd AstroFairy
```

For an existing shallow clone, fetch the missing history before running historical checks. Preserve any
existing work; inspect `git status` before changing files. Use a branch when coordinating simultaneous work.

Follow the [README development setup](README.md#development): Python 3.12+, a project virtual environment,
the runtime/delivery/search hash locks, development tools, and the editable project install. Runtime and
search pins have checked official snapshots; the delivery wheel and upstream source are committed.
Development tools are pinned in `requirements-dev.lock`. Do not reconstruct pins from memory.

Enable the repository hook after cloning; Git does not copy this local setting:

```sh
git config core.hooksPath .githooks
.venv/bin/python -B dev/check.py
```

These are POSIX paths; Windows uses `.venv\Scripts\python`. Linux is the current reference check environment.
See [reported platform issues](STATUS.md#当前收到的问题) before interpreting Windows installation or delivery.
Keep task data separate from installed code and retain old data when changing development-store formats.

## Find the current authority

| Question | Source |
|---|---|
| Current work, release and reported problems | [STATUS.md](STATUS.md), linked release and live AstroFairy Issues |
| Development constraints | [AGENTS.md](AGENTS.md) and the explicit task's authorization |
| Current architecture and enforcement boundary | [architecture.md](docs/guides/architecture.md) |
| Command fields and registered capability contracts | `.venv/bin/python -m astrofairy schema`; runtime parser and declared contracts |
| Work, asset, backup and recovery operations | [operation.md](docs/guides/operation.md), [host protocol](skills/fairy/references/host.md) |
| Original decision rationale | [ADRs](docs/adr/), read with superseding decisions and current architecture |
| Tool pins, test surfaces and mechanical gates | `requirements-dev.lock`, `pyproject.toml`, `governance.toml`, `dev/check.py` |
| Publication | [release workflow](docs/guides/releasing.md) |

ADRs and dated reviews retain their original baseline. For example, ADR-0002 describes the old
`skills/astrofairy/` layout; the current skill is `skills/fairy/`. Old implementation handoffs do not
reactivate unfinished tasks or grant current permissions. Code is observable behavior, not proof that
it satisfies the intended design. If sources conflict, identify the exact claim, baseline and observed
behavior, resolve the design question, and update current guidance without rewriting historical evidence.

## Locate a change

| Responsibility | Owner |
|---|---|
| Main skill and conditional instructions | `skills/fairy/SKILL.md`, `skills/fairy/references/` |
| Protocol parsing and state/admission | `_contracts.py`, `_kernel.py` |
| Durable events, content and runtime composition | `_store.py`, `_runtime.py` |
| Delivery projection and BagIt integration | `_delivery.py` |
| Reusable assets and derived retrieval | `_library.py`, `_search.py` |
| Response documents, selected reads and state recovery | `_documents.py`, `_presentation.py`, `_maintenance.py` |
| Explicit resource safeguards | `_limits.py` and ResourcePolicy |
| Runtime regression tests | `skills/fairy/scripts/astrofairy/tests/` |
| Build, lock, metadata and development checks | `dev/`, `dev/tests/` |

Runtime filenames above are under `skills/fairy/scripts/astrofairy/`. Tests stay with their owner;
new test surfaces must be registered in `governance.toml`. Task-specific workflows belong in assets.

## Make and review a change

1. Read the authorized request or issue, reproduce the behavior where relevant, and state the expected
   contract and affected surfaces. Issue suggestions remain proposals until verified.
2. For a responsibility or architecture change, derive the design from the constraints, compare mature
   implementations using primary sources, and record the decision and limits. Industry standards are
   the minimum baseline; copied names or a green check do not prove equivalent behavior.
3. Repair the cause across affected consumers. Development has no compatibility shims, migrations or
   old-name aliases. Preserve original inputs, observations, historical outcomes and review evidence.
4. Add meaningful regression coverage for a behavior change. Run relevant tests, then the canonical
   check before committing. Ordinary prose/link changes do not need artificial runtime tests.
5. For substantive work, record the request, source revision, change, executed checks and remaining
   limits in `docs/audit/changes/`, updating its index. A new design decision belongs in `docs/adr/`.
   Have consequential design/behavior changes reviewed independently when the task requires it;
   implementation, self-check, independent verification and maintainer acceptance are distinct claims.
6. Commit with Conventional Commits only when authorized; never bypass hooks. Push, tagging, release,
   external messages and access to real business data need applicable task authorization. Follow the
   existing release workflow for publication rather than editing a released tag or asset.

Keep the core's responsibilities small and orthogonal. Put variable policies/data and reusable task
knowledge outside the core; physical line count is not an architectural proof. Essential task steps
must be available to the agent, and user interaction and resources should fit the work. Do not weaken
evidence, permissions or integrity checks to make a workflow appear lighter or a test pass.

## Validation levels

The canonical command is `.venv/bin/python -B dev/check.py`. It runs declared test surfaces, type/style,
skill structure, lock/provenance and metadata checks, plus document references. Default tests do not
download model weights. Historical review checks prove their recorded scope, not present product quality.

Real-model and integration checks are explicit, potentially networked and resource-intensive. Use new
fixture directories and an approved model-cache location. Current raw evidence and preparation details
are described in [evidence.md](docs/development/evidence.md).

```sh
ASTROFAIRY_MODEL_CACHE="$PWD/.cache/fastembed" .venv/bin/python -B dev/evaluate_retrieval.py --root .evaluation/retrieval-check --out .evaluation/retrieval-check/results.json
ASTROFAIRY_TEST_E5=1 ASTROFAIRY_MODEL_CACHE="$PWD/.cache/fastembed" .venv/bin/python -B -m unittest astrofairy.tests.test_search_contracts.SearchContractTests.test_real_e5_model_smoke_when_explicitly_enabled -v
.venv/bin/python -B dev/evaluate_learning.py --root .evaluation/learning-check --out .evaluation/learning-check/results.json
.venv/bin/python -B dev/verify_recovery.py --help
```

The retrieval fixture seeds adopted assets before refresh. Empty-library preparation is separately
reported in issue #2; do not use an empty-library success as proof that the model has been prepared.
Set `ASTROFAIRY_MODEL_CACHE` for learning evaluation too. Real E5 has substantial disk/memory cost; see
the measured [release limits](docs/releases/v0.1.0a2.md). The evaluation scripts currently use Unix
resource accounting. Do not infer Windows/macOS or native-agent coverage from these Linux runs.

For installation integration, install the verified skills CLI locally following the version and Node
requirements in the README, then use `dev/check_installation.py --help`. Pass actual `--node`,
`--skills-cli` and prepared `--python` paths; fixtures stay under an approved `.evaluation/` directory.
The helper exercises copied layouts and scripted protocol work, not native model adherence.
For workflow YAML changes, also run actionlint as required by the release guide. Obtain these optional
tools from their official distributions, verify supplied checksums where available and record versions.
Neither `.tools/` nor the maintainer's prepared `.venv` is a checkout dependency.

## External development organization

The maintainer may organize AstroFairy work through an authorized external development workspace.
Load that workspace's `CLAUDE.md` router and the original applicable method/role packages, then apply
this repository's instructions, current status and task scope. Shared design, execution, independent
verification, arbitration and document-governance methods remain governed by their original definitions.
Record the loaded method identity and limits when claiming formal compliance; a summary is not the method.

All AstroFairy changes, decisions, task records, checks and release artifacts stay in this project.
Use AstroFairy's issue tracker, package layout, test entry and version sources. An external monorepo's
package rules, private/public synchronization, issue addresses, environment pins and registry paths do
not automatically apply here. Method-specific records must be explicitly scoped to AstroFairy rather
than written into a different project's registries. Scope conflicts affecting the task require explicit
resolution, not silent weakening of either contract.

Read external materials only with access and authorization; do not copy private method texts, credentials
or machine paths into this public repository. Without that workspace, a contributor can follow this
guide and the repo's ordinary change/review process. Record unavailable external-method verification
honestly rather than claiming it ran. The runtime, checks and installation have no dependency on that workspace.

On an authorized maintainer machine, the ignored `CLAUDE.local.md` can import that workspace's router
using Claude Code's native import syntax and state its AstroFairy scope. Resolve external references
against their owning workspace. Keep this local file and external paths out of commits and source packages;
ordinary contributors do not need it. Confirm loaded files in the host rather than assuming native loading.

`CLAUDE.md` uses Claude Code's native import of `AGENTS.md` so the shared rules have one source.
See [official import documentation](https://code.claude.com/docs/en/memory#import-additional-files).

## Finish or hand off

Leave the exact branch/commit and any uncommitted files, task/issue links, completed actions, test
results, pending decisions and evidence locations. Update current status when work or release state
changes; preserve dated records. Share necessary ignored evidence using its inventory and checksums,
not an assumption that another checkout contains this machine's caches. A handoff should identify one
concrete next action and the authority needed for it; it should not require this conversation.
