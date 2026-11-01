# Learning and reusable workflows

Observe successes, failures, edits, useful interactions, efficient tool choices and repeated task structures.
Silence is not success; frequency is not proof of usefulness. Retain evidence and applicability.
Keep task facts, personal preferences and behavioral constraints distinct. Apply SCHF-style scope, failure mode,
hardening and explanatory function to constraints; ordinary facts and transient task state are not constraints.

After closure, `feedback` records actual user feedback (`text`, optional `kind`).
`{"op":"learn"}` creates a separate maintenance task with a performance snapshot, including positive feedback.
Use the normal task loop to propose a supported improvement, or finish with an explicit no-change conclusion.
Maintenance does not mutate the delivered task or promote assets by itself.
Use the source's `expected_seq` to reject stale maintenance requests. Source read and child creation share
a transaction; the snapshot records source task and seq. Repeated requests at the same current sequence
can create distinct tasks, so treat this precondition as freshness rather than automatic deduplication.
The maintenance input is a small JSON locator with `document`, source `task` and `seq`. Read it, then use
the free document route from the [host protocol](host.md), for example `read DOCUMENT --task SOURCE_TASK
--pointer /feedback` or `/events`. The source snapshot includes raw events, so forwarded answers and
their order remain available along with calls, reviews and feedback. Read only relevant sections and
all necessary supporting evidence. A snapshot exceeding the ordinary 16 MiB blob limit still uses this
locator contract; it is not silently truncated. Later feedback does not alter the captured document.
Document files and SQLite are separate resources: child rollback may leave an unreferenced derived
file, while source history remains unchanged. No automatic pruning or constant-time replay is claimed.

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
  "evidence":[{"source":"task:SOURCE_TASK_ID","note":"State the observed benefit and its limits"}]
}
```

Kinds are `workflow`, `guide`, `profile`, `case`, `constraint`, `tool-spec`.
Workflow content is structured; other kinds contain text. Tool specifications are passive descriptions:
importing or reading them never installs or executes code.

Proposing returns a candidate reference and a validation task seeded with that exact package.
Read the package, assess the evidence, scope, dependencies and completion conditions, run mechanical checks,
and review `asset-fitness`. Close the validation task only when requirements are met.
For a candidate, read its validation task's input reference with `content.read`; ordinary `asset.read` is for
already adopted assets. The adoption-policy criteria are immutable; retain their checkers and descriptions.
Then `assets adopt <ref> --task <validation-task> --status trial` (or `stable`) makes it searchable.
Candidates are excluded from ordinary search. Import always produces a candidate requiring local validation.

## Discovery

Search considers the current adopted head of each scope/name family before scoring. It compares name,
summary and actual tag string values with Python's Unicode casefold on both sides; JSON serialization
punctuation and content bodies are excluded. The first 16 whitespace-separated terms use literal substring
OR matching. The score counts matching terms, including repeated terms; ties sort by name then scope.
An empty query browses active heads; result limits are 1–10. `assets search --scope` selects a namespace.
This is casefolded metadata lookup, without additional Unicode normalization, accent removal, locale
rules or semantic inference. A missing match is not proof that no useful method exists.

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
