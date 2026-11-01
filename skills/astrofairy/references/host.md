# Host protocol

The conversation host does the reasoning. The local runner manages state and evidence.
Use a single approved writable home. Keep returned task and call ids; users need not manage them.
This development release uses protocol/store format 7. Unsupported existing stores are refused without
migration; choose a fresh approved home for new work.
Use `capabilities --query TEXT` for bounded summaries, then `capabilities --name NAME` for a tool's
actual inputSchema and optional outputSchema. Read full definitions only when needed.
`next` is a read-only work packet and may be repeated without consuming invocation budget.
`schema` is generated from the parser's field table. `expected_seq` rejects stale submissions.
A single-event submit's `seq` identifies its own committed event, not any later concurrent writer.
Refresh next to observe later facts; successful receipt refresh may use a newer snapshot.
For check, it is rechecked when recording the first invocation; the batch retains its initial target and
checks sequence before subsequent calls. Earlier observations remain if later work conflicts.

## Bounded responses and free context reads

Every CLI JSON response fits 24 KiB of UTF-8 including its newline and escaping. Small responses are
complete inline values. A response with `deferred: true` instead supplies a complete immutable
`document` handle, `task` scope, byte count, `control` fields, collection counts and available blocker or
artifact refs. Treat it as a locator, not a truncated complete result. Check the original exit status;
deferral does not turn a failed invocation or mechanical check into success.

Use `read DOCUMENT --task TASK --pointer /goal` for a task response, or omit `--task` for global documents.
Pointers follow RFC 6901 string syntax: `/criteria/0`, `/pending/0`, `/user_updates/0/payload/text`,
`/calls/0/result`, `/spec/goal`; escape `~` as `~0` and `/` as `~1`. The default empty pointer selects the
whole original response. Missing values are errors, not defaults. Huge keys can be inspected through
root fragments without putting the key on a command line.

`read` returns canonical JSON text fragments, not necessarily complete JSON values. Preserve `document`,
`selection`, pointer and `next_offset` together; repeat the same pointer with `--offset NEXT_OFFSET` until null.
Concatenate `text` fragments to recover the selected JSON, then interpret it. Offset/limit count Unicode
characters in that canonical text; the server can return fewer characters to fit the final byte cap.
`--limit` is 1–24576, default 24576. Do not assume a fixed fragment size. Reads are free: no capability,
invocation charge, event, revision or closed-task restriction. They cannot be used as tool evidence.

`document` commits an owner-bound typed root; `selection` commits its typed subtree. Neither is the
SHA256 of the returned text or an artifact ref. Fragments authenticate the consumed blocks and
navigation, reported as `integrity: "selected"`. Unread sibling damage may remain undetected.
Use free `audit-document DOCUMENT --task TASK` (omit task for global documents) to check all reachable
blocks, spans, scalar encoding and key ordering. It returns `integrity: "full"`, `verified_nodes` and
`canonical_sha256`: compare the latter with SHA256 of a complete canonical-text reconstruction.
Full audit traverses the graph/content and may materialize a large scalar; use it for whole-document integrity,
not automatically on every fragment. Both commands fail safely for damaged consumed data or wrong scope.

Read the relevant goal, criteria and assumptions before acting. Compare seq/revision and collection
counts when refreshing `next`; consume every unprocessed forwarded answer in order, preserving its
event id for `user_basis`. Counts do not assert that all details were shown or read. Inspect the
identified pending/conflicting call and its pinned definition. Reuse immutable context already read;
after context loss, recover the necessary earlier records rather than assume they were processed.
The `/workspace` field remains reachable when deferred. A new task state never changes old documents.
For deferred delivery, read `/artifact_path` and `/receipt_path` before giving the user those links.

`projection_failed` means work may already be committed. It retains authoritative task/call and newly
created learning/validation task ids when available. Inspect those identities before any retry; for a
failed start response, resume the returned task rather than create another. Nested tool fields do not
become recovery identities. Missing/corrupt documents fail explicitly; keep the approved home intact.
Native Python Workshop methods and on-disk receipts remain full values. This CLI limit is not a token,
replay-time, disk or whole-conversation limit. Documents share unchanged values and collection subtrees;
append histories reuse completed prefixes. Early insertion can shift metadata groups; creating snapshots
still traverses native input. Event replay and retention remain separate work, without automatic pruning.

## First task

Run `start --request <original-request> --input <attachment>` (repeat `--input` for attachments).
An optional `--spec <file>` carries goal, criteria and assumptions. Each criterion has `id`,
`description`, `checker`, `parameters`, `origin`, `required`, and `basis`.
Use `origin: user` for explicit requirements; derived criteria remain revisable.
The runner's asset-validation criteria use `origin: policy` and cannot be weakened by a task strategy.
The defaults are provisional: relevant content (semantic) and nonempty bytes (mechanical).
Omit initial fields to use defaults. Supplied null/wrong types fail before task creation; valid assumptions
are stored in created at revision 1. Python callers pass these fields via `Workshop.start(request, spec={...})`.
Adapt criteria to the real deliverable. Available checkers are `semantic`, `nonempty`, `json`, `contains`.
`contains` takes `parameters: {"text": "required text"}`. More capabilities can be registered in Python.
Use `--read-only` when task operations must not write files. Internal records and delivery snapshots
still use the approved state directory. These effects do not authorize external host actions.
Capability effect classes are exactly `reason`, `read`, `write`; sends and deletions are writes.
An uncertain write blocks identical retries. New capability business names do not create new permission classes.

## Submit JSON

Run `submit <task> --file <json-file>` or provide JSON on stdin.

For conversation work:

```json
{"op":"request","purpose":"Produce the agreed deliverable","refs":[]}
```

The returned call id identifies the pending work. Submit the actual content:

```json
{"op":"report","call":"RETURNED_CALL_ID","text":"Actual deliverable","name":"result.md"}
```

This returns a content reference. Submit `{"op":"publish","ref":"CONTENT_REFERENCE"}`.
After interruption, `next` can suggest `publish` with one `publish_candidate`; inspect the task for alternatives.
For real files created by host tools, put them in the `workspace` returned by `next`, then invoke
`file.capture` with a relative path. Raw bytes are retained without decoding.

Registered calls use `{"op":"invoke","capability":"NAME","parameters":{}}`.
Look up the accepted value contract through `capabilities --name NAME`. Invalid values are rejected
before invocation or budget charge. Asset search returns metadata;
reading an adopted asset pins its exact version. Read large inputs with bounded `content.read` fragments.

Run `{"op":"check"}` for mechanical criteria, then semantic reviews:

```json
{"op":"review","criterion":"goal","verdict":"pass","basis":"Explain the concrete comparison with the goal","evidence":["CONTENT_REFERENCE"]}
```

Use `fail` or `unknown` when appropriate. Close with `{"op":"close","outcome":"complete"}`.
Reviews target the agreement revision and immutable content reference. Republishing the same content
preserves prior judgments; a new pass must explicitly `replaces: [REVIEW_EVENT_ID]` to retire a prior failure.
Mechanical reviews link a successful recorded `content.check` call and its exact checked ref, checker,
parameters, verdict and basis. Custom check handlers must return this witness as
`checked: {ref, checker, parameters}`; contradictory or missing evidence cannot become a review.
Other outcomes are `partial`, `failed`, `cancelled`. The runner writes the artifact and receipt under
its delivery directory. `deliver <task>` can regenerate that export. `inspect <task> --history` shows events.
Invocation budget limits new calls. Existing reports, answers, publication and semantic review remain
available at zero budget; required mechanical checks still need a registered call. Follow current issues.

CLI SQLite runtime failures return nonzero `storage_failed`, a safe message, and `sqlite_code`/`sqlite_name`
when available. Preserve the store and inspect state before retrying. Version refusal remains `version`.
Invocations contain contract_ref. Read one historical definition through `inspect TASK --contract REF`;
ordinary inspect/receipts retain references without injecting full schemas. Adapter authors read
[tool contracts](tools.md); schemas and imported asset documents do not execute code.

If a pending writer has a pinned reconciler, inspect that definition, then use the read capability with
exactly `{call: ORIGINAL_ID}`. The runner derives confirmation from a genuine final observation, without
a separate status declaration or accept-proof command. The read uses ordinary permission and budget.
Do not repeat the writer after confirmation. Publish the appropriate confirmed artifact and check the
current agreement; extra verifier outputs may be evidence rather than the deliverable.
Follow [recovery rules](review.md) for nonfinal results, missing capabilities or conflicts.

## Human input

Use `ask` with `question`, `recommendation` and optional `options` only for a consequential choice.
Forward the user's actual answer or unsolicited steering with `answer` and `text`.
It changes the task revision. Reconcile the goal and recheck affected output.
`revise` takes `goal`, `criteria`, `reason` and optional `assumptions`.
A canonical no-op revision is recorded but does not invalidate checks. Real agreement changes do.
Changing explicit criteria additionally needs `user_basis`, the event sequence of the new forwarded answer.
The runner validates that such an event exists; the host is responsible for forwarding it faithfully.


## Administrative recovery

Keep the approved home; events, captured content, asset versions and document blocks do not expire
automatically. Retirement changes selection, preserving old pins. The agent, not the member, handles
explicit audit/backup/restore through the [operation guide](../../../docs/guides/operation.md).
`audit-state` is read-only; `backup --out NEW_DIRECTORY` captures main then document state with native
SQLite backup; `verify-backup DIRECTORY` verifies it; `restore DIRECTORY --out NEW_HOME` validates a
fresh home. These are full maintenance operations, not free constant-time context fragments.
Uncaptured workspace files, exported copies, environment/credentials and external-service state are
excluded. No handlers run or effects retry during recovery. Retain unknown/pending identities and
investigate them normally. An incomplete restore is blocked by restore.pending; do not bypass it.
Learning inputs expose `source_document` alongside their ordinary content locator: it is an explicit
owner-bound reference used for retention/audit, and must equal the referenced locator bytes/metadata.

Backup preserves captured record bytes exactly, including any credentials already present in them.
The environment/credential exclusion concerns uncaptured external files; it does not promise filtering
or redaction of captured events, blobs or documents. Treat backups with the same access control as records.
