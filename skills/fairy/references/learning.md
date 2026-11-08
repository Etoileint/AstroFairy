# Learning and reusable workflows

Observe successes, failures, edits, useful interactions, efficient tool choices and repeated task structures.
Silence is not success; frequency is not proof of usefulness. Retain evidence and applicability.
Keep task facts, personal preferences and behavioral constraints distinct. Apply SCHF-style scope, failure mode,
hardening and explanatory function to constraints; ordinary facts and transient task state are not constraints.

After closure, `feedback` records actual user feedback (`text`, optional `kind`). The closed task's
`next` exposes `maintain`, `defer` and `no_change` choices whether or not the local export currently
validates; learning decisions do not wait for a derived file. `defer` records a visible todo for a later
session; `no_change` is an explicit evidence-backed conclusion; `{"op":"learn","decision":"maintain"}`
records the source decision, creates a separate maintenance task with a performance snapshot and links
the child id. `todos` (or `Workshop.todos()`) discovers unresolved deferred decisions across tasks without
requiring a task id. Use the normal task loop to propose a
supported improvement. Maintenance records its decision on the source; it does not revise the source's
delivered content or promote assets by itself. Source snapshot, child creation and linked source decision
share one main-database transaction. The snapshot records the source task and sequence before the decision;
the reply reports the committed decision sequence. A failed child or decision write rolls back both.
Use the source's `expected_seq` to reject stale maintenance requests: after success, retrying that sequence
conflicts. Requests without this precondition, or with a newly read sequence, can create another child;
the sequence is a freshness precondition rather than a durable idempotency token.
The maintenance input is a small JSON locator with `document`, source `task` and `seq`. Read it, then use
the free document route from the [host protocol](host.md), for example `read DOCUMENT --task SOURCE_TASK
--pointer /feedback` or `/events`. The source snapshot includes the recorded facts and raw events under
one labelled history; a separate `current_assessment` carries the live checker-contract identity and
current issues, so changed installed checkers do not rewrite the historical record. Forwarded answers
and their order remain available along with calls, reviews and feedback. Read only relevant sections and
all necessary supporting evidence. A snapshot exceeding the ordinary 16 MiB blob limit still uses this
locator contract; it is not silently truncated. Later feedback does not alter the captured document.
Document files and SQLite are separate resources: child rollback may leave an unreferenced derived
file; failed main-database writes leave no committed child or source decision. No automatic pruning or
constant-time replay is claimed.

## Candidate contract

Run `assets propose <file>` with exactly these fields:

```json
{
  "name":"clear-summary",
  "scope":"personal",
  "kind":"workflow",
  "summary":"Organize a concise summary with traceable source claims",
  "tags":["summary","sources"],
  "content":{"inputs":["source"],"parameters":{},"steps":[
    {"instruction":"Identify the audience's decision and relevant source claims","done":"Claims have source locations"},
    {"instruction":"Write and check the summary","done":"Necessary claims are covered and additions are identified"}
  ]},
  "evidence":[{"source":"task:SOURCE_TASK_ID","note":"State the observed benefit and its limits"}],
  "applicability":{"use_when":["internal summary"],"avoid_when":["legal advice"]},
  "dependencies":["source note"],
  "invalidation":["audience changes"]
}
```

`applicability`, `dependencies` and `invalidation` are optional structured fields; they remain in the
package and enter the retrieval projection rather than disappearing into a free-form workflow blob.
Kinds are `workflow`, `guide`, `profile`, `case`, `constraint`, `tool-spec`.
Workflow content is structured; other kinds contain text. Tool specifications are passive descriptions:
importing or reading them never installs or executes code.

Proposing returns a candidate reference and a validation task seeded with a one-member snapshot containing
that exact package under the `candidate` role. Read the package, assess the evidence, scope, dependencies and
completion conditions, run mechanical checks, and review `asset-fitness`. Close the validation task only when
requirements are met. For a candidate, read its validation task's input reference with `content.read`;
ordinary `asset.read` is for already adopted assets. The adoption-policy criteria are immutable; retain their
scopes, targets, checkers and descriptions. Adoption requires the current snapshot to contain the exact
candidate member and active policy reviews bound to that content and member descriptor; candidate bytes merely
appearing in a collection are insufficient. Then `assets adopt <ref> --task <validation-task> --status trial`
(or `stable`) makes it searchable. Candidates are excluded from ordinary search. Import always produces a
candidate requiring local validation.

## Discovery

Search projects the current adopted head of each scope/name family into a local LanceDB index. Chunks cover
name, summary, tags, applicability/inputs/parameters, workflow steps, body and evidence; BM25 with bundled
ICU segmentation, exact-vector multilingual E5 results and weighted RRF (full-text 2:1) are fused. The fixed profile records the
model source/revision, the six actually consumed files with SHA-256 (ONNX model, external data, tokenizer
and three tokenizer/config JSON files), tokenizer, prefixes, normalization and field/chunking scope. Each
query returns the source generation, profile and table version; a stale or unavailable projection returns
`search_not_ready` with the offending stage and an explicit recovery route. `assets prepare` downloads when
absent and SHA-256-verifies all six files without building an index or running inference;
`assets search --refresh` composes the same preparation with a projection rebuild, and an empty active
library returns `projection.state=empty` with the preparation result. Ordinary search uses the fixed local
directory, does not download or start another model. Empty queries browse active heads; `asset.search` defaults to 8, ordinary CLI
pages default to 50, and either accepts up to 200 plus an opaque `cursor` from `next_cursor` (the agent
capability also uses `cursor` in its parameters). A cursor binds the
query, scope, kind, source generation, profile, table and version; changed state returns a conflict or
`search_not_ready` instead of mixing pages. `--scope` and `--kind` filter discovery. Candidates and retired
heads do not enter ordinary discovery. The index is a rebuildable
cache; SQLite asset events remain the authority. A missing match is not proof that no useful method exists,
and similarity is not an applicability or adoption decision.

A task agreement may fix adopted `governance` asset refs. `governance --scope personal|team` lists adopted
constraint assets and their structured applicability/dependencies/invalidation; `governance_scope` in
the start spec fixes matching refs automatically. Read and pin them before completion; search top-k never
determines required rules, and unknown applicability remains an explicit host judgment.
Success can revise an existing method or its recommendation rather than add a new asset.
A changed base rejects stale adoption. Rebase as a new candidate and revalidate. Reverting likewise creates
a new version from the previous content. `assets retire <ref>` removes that version from active selection;
the latest remaining approved version may become the head. Historical references remain readable.

## Sharing

When requested, `assets export <ref> --out <file>` writes a portable JSON package.
`assets import <file>` verifies its content digest and creates a local candidate.
The bundle contains the selected asset and provenance notes, not the task ledger or attachment blobs.
Import retains sender-declared evidence notes under bundle provenance; it does not turn them into local observations.
Personal/team scopes are local namespaces, not account permissions or a remote sharing service.


Learning input descriptors also register the immutable locator as `source_document`. The content blob
remains the read input; the typed link lets state audit verify the exact document owner/bytes/sequence
without guessing references in arbitrary JSON or provenance text. Retirement never deletes history or
pinned content. Recorded-state backup retains all document blocks, including separately issued handles.
