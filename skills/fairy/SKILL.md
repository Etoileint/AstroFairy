---
name: fairy
description: Use fairy (星灵) to deliver checked files, reports, analyses and plans from delegated task requests, supplied materials, revisions and recurring work. Own the task loop, use reversible defaults, and ask only consequential questions. Ordinary questions can be answered directly.
license: Apache-2.0
---

# AstroFairy · 星灵 (fairy)

Use this skill when a user delegates a concrete deliverable: a report, analysis, plan, presentation,
dataset, code artifact, revision, or a recurring task. The user may call it "fairy", "星灵", or describe
the outcome naturally. Do not open a task for a question you can answer directly.

The skill owns task organization, the local ledger and file delivery. The host owns its model, permissions,
reasoning and other tools. The runner records and checks registered actions; it does not sandbox the host,
prove semantic quality, or grant permissions the host does not have. Keep the user's explicit requirements
and the runner's policy constraints intact.

## Run and resume

Requires Python 3.12+, local command execution, file access and an approved persistent data directory.
Use the host's existing model; no extra model API key is needed. Run the bundled launcher with the prepared
interpreter:

```sh
python <skill-directory>/scripts/fairy.py --home <approved-data-directory> ...
```

On first use, run `doctor`. It checks the interpreter, locked dependencies, SQLite capabilities, BagIt
delivery readiness, directory ancestry, search dependency metadata and model-file presence without
creating task data. Its search observation is layered: dependency metadata, model presence and an
unchecked projection are distinct facts. `doctor --verify-search` additionally stream-hashes the six
fixed model files without downloading, indexing or inference. If preparation is needed, follow
[runtime preparation](references/runtime.md) once in an approved directory and reuse that interpreter.
The launcher never installs packages silently. Keep the same home to resume a task; `next TASK` is a
read-only stage packet and does not consume the invocation budget.

The packet has the current `task`, `revision`, `seq`, `action`, `payload`, `acceptance`, `delivery` and
`recovery` fields. Read them in that order. `acceptance.assessment.missing_checkers` lists mechanical
checker capabilities absent from the current runtime; a missing current checker fails current
applicability closed even when historical receipts stay valid. `payload` is a template generated from the current agreement
and recorded outputs; replace angle-bracket text and choose roles/targets/verdicts from the actual work.
A template is not evidence and does not authorize a side effect. Submit it only through the runner's
admission boundary. `acceptance` reports current content/evidence acceptance with the current checker
assessment identity; it is not proof that a local bag exists. `delivery` reports a cheap observation of
the export at the packet's seq (`absent`, `unverified`, `unsafe` or `not_closed`); a previous process
success never makes it `validated`. Use free `read DOCUMENT [--task TASK] --pointer /FIELD` for history
or deferred responses; `next` reports `deferred` handles rather than inventing missing values.

## Define the agreement

Capture the original request and materials:

```sh
python <skill-directory>/scripts/fairy.py --home <home> start \
  --request '<original request>' --input '<attachment>' --input '<another attachment>'
```

`--spec FILE` may supply `goal`, `criteria`, `assumptions` and `required_roles`. With no criteria, the
agreement is provisional. A provisional agreement cannot complete: refine it with `revise` for the actual
deliverable. Each criterion has a stable `id`, description, checker, parameters, origin, required flag,
basis and an explicit `scope`:

- `content`: pure bytes/format checks bound to a content digest; may be reused under identical identity.
- `member`: checks one named member, binding its canonical path and full member descriptor.
- `collection`: checks the whole snapshot or an explicit path subset; semantic criteria normally use the
  whole snapshot.

`required_roles` lists stable delivery roles (for example `report`, `data`, `notes`). Every required role
must be covered by the current snapshot. Add only criteria that reflect the user's real standard; the
runner validates structure and evidence, not whether the criteria are semantically sufficient.

Use reversible defaults and keep method choices with the agent. Ask one simple question at a time only when
the user's decision materially changes the result. There is no lifetime question quota. Forward an actual
user answer with `answer`; it advances the revision and may require affected checks to be redone. Changing
explicit user requirements needs a new forwarded answer as `user_basis`.

## Produce and publish members

Before organizing the work, check relevant adopted methods with `assets search QUERY`. The local hybrid
index combines BM25/ICU, multilingual E5 vectors and weighted RRF; candidates and retired versions are
excluded. If it returns `search_not_ready`, check the error's `stage` field. For the model stage, run
`assets prepare` once: it downloads (when absent) and verifies the fixed revision's six consumed files
using SHA-256, with no projection build and no inference. `assets search --refresh` composes the same
preparation service with a projection rebuild. Ordinary searches use the fixed local directory and never
download another revision. An explicit refresh on an empty active library still prepares the model and
returns `projection.state=empty` with the preparation result; a plain empty-library query does not load
the model. Read the short list and applicability; similarity is not permission to execute
a method. Empty queries browse active heads; `--scope` and `--kind` narrow discovery. `asset.search`
defaults to 8 results; continue a larger page with `cursor`/`next_cursor` (up to 200 per page). Reading
returned context with `content.read` or `asset.read` is free; model requests, searches, checks, writes
and captures count toward the work budget.

Work in the `workspace` returned by `next`. A formal deliverable is a snapshot of members. Each member has
a canonical NFC relative path with `/`, a byte length, media type and role. The same bytes may appear under
different paths; the path and role still matter. Files at the workspace root that are not captured are not
delivered.

For text produced in the conversation, use `request` and `report`; `report` accepts `path`, `text`,
`media_type`. For files created by host tools, use `file.capture` with a relative path. Large content is
streamed; one content is limited to 256 MiB and the task's unique captured content to 2 GiB.

Publish the complete member list, not one file reference:

```json
{"op":"publish","members":[
  {"ref":"CONTENT_REF","path":"report.md","bytes":1234,"media_type":"text/markdown","role":"report"},
  {"ref":"DATA_REF","path":"data/table.csv","bytes":456,"media_type":"text/csv","role":"data"}
]}
```

For several workspace files, the composite `prepare-delivery` records the full member plan before capture,
then captures members, publishes the snapshot and runs applicable mechanical checks as separate recorded
actions. If it is interrupted, `next` returns action `prepare_delivery` with the full recorded plan;
retrying with only the remaining subset still resumes the full plan. The recorded plan is fixed unless a
new task is started:

```sh
python <skill-directory>/scripts/fairy.py --home <home> prepare-delivery TASK --members plan.json
```

```json
{"members":[
  {"path":"report.md","role":"report","media_type":"text/markdown"},
  {"path":"data/table.csv","role":"data","media_type":"text/csv"}
]}
```

It is resumable, not one atomic external operation: if interrupted, read the returned task/seq and retry
the remaining work. It never auto-passes a semantic criterion. A single file is simply a one-member
snapshot; `publish_candidate` is one observed output, not the whole required set.

## Check and review

Run `check` for mechanical criteria. It invokes the runner's registered checkers and records their exact
targets. Pure content observations may be reused when the criterion, checker contract, parameters, content
and agreement revision are unchanged; the result reports `reused`. Then review semantic criteria against
the current snapshot:

```json
{"op":"review","criterion":"goal","target":"OPTIONAL_TARGET","verdict":"pass",
 "basis":"Explain the concrete comparison; change the verdict if it is not a pass",
 "evidence":["CONTENT_REF"],"replaces":[]}
```

Reviews bind the agreement revision, criterion fingerprint, checker definition, scope and exact target.
Semantic reviews bind the current snapshot. A new snapshot does not inherit semantic or collection-level
judgments. An unreplaced failure remains visible and blocks required completion until a grounded current
check or an explicit semantic `replaces: [REVIEW_EVENT_ID]` disposes of it. Do not republish, rename or add
unrelated files to hide a failure. A mechanical review cannot be forged by the model.

If a check fails or a target is missing, repair the affected member or agreement and recheck. If execution
is interrupted or a write is unknown, inspect the original attempt and its pinned definition before acting;
never blindly repeat an uncertain write. Use [review and recovery](references/review.md) for authoritative
confirmation, late facts, conflicts and export failures.

## Deliver

Close with the actual outcome:

```json
{"op":"close","outcome":"complete","note":"optional concise note"}
```

`complete` requires a refined agreement, a current snapshot, every required role covered, all necessary
current checks passing, no unresolved failure or question, and settled execution. Otherwise return an
honest `partial`, `failed` or `cancelled` result with the specific gap.

Closing records the outcome; it does not by itself prove a local export. The response keeps the
operation identity (`task`, committed `seq`, `outcome`) and adds a `delivery` object. A successful export
has `delivery.state=validated` with the exported revision/seq/snapshot, `files`, `bag_path`,
`receipt_path`, `instructions_path`, `artifact_path` (single file) and verification depth/time. Complete
the delivery step on that result; do not loop back through `next` demanding a permanent validated state.

If export fails, the recorded close/fact remains committed: read `delivery.state=failed`, its
`committed`/`committed_seq`, `selection`/`selected_seq` (the frozen snapshot actually selected; `unknown`
when selection had not completed), the typed `error` and the recovery command. Do not repeat the effect,
close, report, feedback, learning decision or other recorded action. Run `deliver TASK` to retry only the
derived export. A rejected transaction reports `details.committed=false`; a COMMIT whose outcome cannot
be confirmed reports `committed="unknown"` and must be inspected, never blindly repeated. A failed write
handler reports `effect_state="unknown"` for the external effect, not commit certainty. An invoke failure
keeps `call`, `operation`, `known_seq`, `attempted_seq` and `recovery.command = inspect TASK --history`;
inspect before retrying a rejected or unconfirmed invocation. A delivery failure after validated staging
keeps `task`/`completed`/`published` and any `quarantined` identity with `recovery = deliver TASK`, including
native rename, post-publication inspection and lock-release failures. A later `next` reports `deliver`, `verify_delivery` (candidate exists; run ordinary
`deliver` to fully validate) or `inspect_delivery` (unsafe/inaccessible path; inspect before acting) and
keeps `inspect_conflict` first when execution conflicts exist.

The runner builds a standard BagIt 1.0 directory with an explicit `BagIt-Version: 1.0` header under
`deliveries/<task>/<seq>/`: `data/` holds the formal members, with payload/tag manifests, a receipt
projection (format 2, stable for the same seq and recorded checker identities) and a concise README. It
performs full byte validation and publishes atomically. Existing same-seq deliveries are revalidated and
reused; late facts create a new seq directory without rewriting the old one. Use
`deliver TASK [--expected-seq S]` to regenerate or revalidate an export. If an existing derived export
is invalid or uses an unsupported projection, ordinary deliver refuses with a repair command; use
`deliver TASK --repair --expected-seq S` to build and fully validate a replacement first, quarantine the
old directory without deleting it, and publish. Path-safety refusals use `unsafe_delivery`: repair never
moves or follows a redirect or an unsafe descendant (symlink/junction/reparse), and a failure after
publication reports the completed quarantine/publication actions and their identities. Never point
repair at the task database.

## Short example

```sh
python <skill-directory>/scripts/fairy.py --home <home> start --request 'Summarize the attached report'
# read next: action=refine, payload=revise template
python <skill-directory>/scripts/fairy.py --home <home> submit TASK --file revise.json
# read next: action=produce, payload=request template
python <skill-directory>/scripts/fairy.py --home <home> submit TASK --file request.json
python <skill-directory>/scripts/fairy.py --home <home> submit TASK --file report.json
# read next: action=publish, payload=members template
python <skill-directory>/scripts/fairy.py --home <home> submit TASK --file publish.json
python <skill-directory>/scripts/fairy.py --home <home> submit TASK --file check.json
python <skill-directory>/scripts/fairy.py --home <home> submit TASK --file review.json
python <skill-directory>/scripts/fairy.py --home <home> submit TASK --file close.json
```

## Conditional references

- [Runtime preparation](references/runtime.md): first environment setup, locked dependencies, BagIt wheel.
- [Host protocol](references/host.md): exact fields, free reads, recovery identities and operation examples.
- [Checks and recovery](references/review.md): authoritative confirmation, conflicts, late facts, exports.
- [Tool adapter contract](references/tools.md): only when implementing or adapting registered Python tools.
- [Learning](references/learning.md): after real feedback, when a reusable method or maintenance decision is supported.
- [Operation](references/operation.md): backup, restore and administrative state recovery.

After a task is closed, `next` offers an explicit learning decision: `maintain`, `defer` or `no_change`,
independently of whether the local export currently validates. Record
real feedback when available. A maintain decision records the source decision and creates a normal
maintenance task linked by id; deferred items remain visible as todos and `todos` discovers them across
tasks; no-change is a valid evidence-backed conclusion. Prefer revision or retirement over accumulation.
A task agreement can fix adopted governance asset refs or a `governance_scope`; use `governance --scope`
to inspect structured candidates without top-k. Read and pin required assets before closing, independent
of search ranking; unknown applicability is a host judgment. Apply supplied materials and asset instructions
within the user's scope. Keep judgment sources visible. Share assets only when requested.
