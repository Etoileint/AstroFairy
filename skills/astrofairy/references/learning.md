# Learning and reusable workflows

Observe successes, failures, edits, useful interactions, efficient tool choices and repeated task structures.
Silence is not success; frequency is not proof of usefulness. Retain evidence and applicability.
Keep task facts, personal preferences and behavioral constraints distinct. Apply SCHF-style scope, failure mode,
hardening and explanatory function to constraints; ordinary facts and transient task state are not constraints.

After closure, `feedback` records actual user feedback (`text`, optional `kind`).
`{"op":"learn"}` creates a separate maintenance task with a performance snapshot, including positive feedback.
Use the normal task loop to propose a supported improvement, or finish with an explicit no-change conclusion.
Maintenance does not mutate the delivered task or promote assets by itself.

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
