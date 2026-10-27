# AstroFairy · 星灵

**Structured AI task delivery with traceable checks and reusable workflows.**

English · [简体中文](README.zh-CN.md)

AstroFairy is an [Agent Skills](https://agentskills.io/specification) package that helps an existing
AI agent turn a task request and source materials into a usable deliverable. The agent handles
clarification, organization, execution and review; a small Python runtime maintains the task record.

Give it a task, provide the relevant files, and answer an occasional consequential question.
Receive the result, a concise account of its assumptions and limitations, and a detailed receipt
when you need to inspect the work.

> Early alpha: the local runtime and portable skill are implemented. Native application discovery,
> plugin management and update behavior have not been verified in every supported installation target.

## Install

Requirements:

- An agent application that supports Agent Skills, local commands and file access.
- Python 3.12+ for the bundled runtime. No third-party Python packages or additional model API key.
- Node.js/npm for the [skills CLI](https://github.com/vercel-labs/skills) installer.
- A writable, persistent data directory for task history and reusable assets.

Install from GitHub into the current project:

```sh
npx skills@latest add Etoileint/AstroFairy --skill astrofairy --copy
```

The installer lets you select the target agent. For an unattended, user-wide installation, specify
the agent and add `-g --yes`:

```sh
npx skills@latest add Etoileint/AstroFairy --skill astrofairy --agent codex --copy -g --yes
```

| Application | `--agent` value |
|---|---|
| Codex | `codex` |
| Claude Code | `claude-code` |
| Cursor | `cursor` |
| GitHub Copilot | `github-copilot` |
| Gemini CLI | `gemini-cli` |

These five installer targets have passed project-level copy and isolated runtime tests.
The tests do not establish that every native application loads or invokes the skill correctly.
Private repositories require Git credentials with access to the repository.

For a local checkout, replace `Etoileint/AstroFairy` with its directory path. For manual installation,
copy the entire `skills/astrofairy/` folder into a skill directory supported by your application.
The folder is self-contained; no separate `pip install` is needed. If the application does not show
the new skill immediately, reload its skills or start a new session.

## Use

For the first session, ask your agent:

> Use astrofairy. Check the environment and initialize a persistent directory for tasks and reusable assets.

Then attach your materials and delegate the work:

> Use astrofairy to make a presentation from this report for our internal review.

> Use astrofairy to compare these proposals and recommend a practical next step.

> Revise the result for the new audience, keeping the source figures unchanged.

The agent chooses an approach, manages task identifiers and checks the actual result. It asks for
your decision when that decision materially affects the outcome. Ordinary questions can be answered
directly without opening a task. Explicitly naming `astrofairy` makes your intended skill clear;
automatic selection depends on the host application.

## How it works

1. **Define:** capture the request and materials; derive the goal, checks and important assumptions.
2. **Produce:** retrieve relevant assets and execute an appropriate workflow until an artifact exists.
3. **Check:** run applicable mechanical checks and review the artifact against its semantic criteria.
4. **Deliver:** return the artifact and receipt, with an honest complete, partial, failed or cancelled outcome.

Original inputs and output bytes are retained. Reviews bind to the task revision and artifact version,
so a changed result needs fresh checks. Tool observations and model judgments remain distinguishable.
The receipt records the goal, assumptions, inputs, actions and review basis for inspection.

The host supplies the model and task-specific tools. Document creation, rendering, browsing and other
specialist capabilities depend on the tools available in that host; AstroFairy does not bundle every
file-format engine.

## Learning and sharing

Successful approaches, corrections, feedback and repeated task structures can support improvements
to an external asset library. Methods and workflows are retrieved as needed rather than accumulated
in always-loaded instructions.

After delivery, the agent can propose a reusable asset, validate it through a separate task and adopt
it for trial or stable use. Assets can be revised or retired. Maintenance can also conclude that no
change is warranted. Exported assets are portable JSON packages; imported assets require local validation.
Sharing is currently file-based. Team account permissions, remote synchronization and automatic background
maintenance are not implemented.

## Data and trust

Keep the data directory separate from the installed skill so that updates preserve history and learning.
The runtime accepts an explicit `--home`; otherwise it uses `ASTROFAIRY_HOME`, then
`~/.local/share/astrofairy`. The host must have permission to use the chosen location.

AstroFairy is a cooperative agent workflow with local checks. It does not sandbox the host or independently
certify semantic quality. Model reviews remain model reviews; local integrity hashes are not external
attestation. An interrupted action with an uncertain result blocks complete delivery until resolved.
Invocation and content budgets are enforced locally; actual model tokens and wall time remain host-managed.
See the [architecture and enforcement boundary](docs/guides/architecture.md).

## Development

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python dev/check.py
```

These commands use POSIX virtual-environment paths; on Windows use the corresponding `.venv\Scripts\python`.
Enable local checks before commits with `git config core.hooksPath .githooks`.

Build the optional Python package and portable skill archive:

```sh
.venv/bin/python -m build --no-isolation
.venv/bin/python dev/package_skill.py
```

The standard skill folder is the canonical distribution unit. `dist/astrofairy.zip` contains that same
folder without development files. The optional wheel builds the same runtime source.
`.claude-plugin/` provides optional native plugin metadata; native managed installation and updates
have not been verified here. There is no marketplace listing implied by those files.

Protocol lookup and a minimal developer task:

```sh
python -m astrofairy schema
python -m astrofairy --home .fairy doctor
python -m astrofairy --home .fairy start --request 'Prepare a source-based project brief'
```

The parser owns command fields, `requirements-dev.lock` owns development tool versions, and
`governance.toml` declares test surfaces and growth budgets. After changing package metadata or the
root license, run `python dev/sync_metadata.py`; check mode and CI reject stale generated files.
Validation is documented in the [initial report](docs/reports/initial-validation.md) and
[distribution comparison](docs/reports/mattpocock-alignment.md). Operational details are in the
[operation guide](docs/guides/operation.md).

## Acknowledgments and license

The skill packaging and instruction design draw on
[Matt Pocock's skills](https://github.com/mattpocock/skills), including their guidance on progressive
disclosure, clarification and environment improvements. AstroFairy is an independent implementation.

Licensed under [Apache License 2.0](LICENSE).
