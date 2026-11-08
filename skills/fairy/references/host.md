# Host protocol

The conversation host does the reasoning. The local runner manages state and evidence.
Use a single approved writable home. Keep returned task and call ids; users need not manage them.
This development checkout uses protocol 11, stage packet 2, receipt projection 2 and store format 10.
Unsupported existing stores or receipts are refused without a task-store migration; choose a fresh
approved home for new work. An unsupported derived receipt can be rebuilt explicitly with `deliver --repair`.
Use `capabilities --query TEXT` for bounded summary pages (default 12, up to 100, `--cursor`), then
`capabilities --name NAME` for a tool's
actual inputSchema and optional outputSchema. Read full definitions only when needed.
`next` is a read-only stage packet and may be repeated without consuming invocation budget. It returns
`stage_packet_version` (2), `task`, `revision`, `seq`, `action`, `payload`, `acceptance`, `delivery`,
`deliver_command`, `inspect_command` and `recovery`.
`payload` is a submission template generated from the current agreement and recorded outputs; replace
angle-bracket text and choose roles/targets/verdicts from the actual work. A template is not evidence and
does not authorize an effect. `acceptance` reports current content/evidence acceptance (provisional state,
required roles/criteria, open issues, unresolved failures, pending questions, execution settlement) with
the current checker-contract assessment identity; it does not certify a local export. `delivery` is a
cheap observation for the packet's seq: `not_closed`, `absent`, `unverified` or `unsafe`.
`acceptance.assessment.missing_checkers` names mechanical capabilities absent from the current runtime;
missing current checkers make current acceptance fail closed while historical receipts remain reusable. A prior
process's success never makes it permanently `validated`; a successful `deliver` returns
`delivery.state=validated` for the operation that just completed. Closed tasks map to action `deliver`
(absent), `verify_delivery` (candidate exists; run ordinary `deliver` to fully validate) or
`inspect_delivery` (unsafe/inaccessible path); `inspect_conflict` keeps precedence. Use
`deliver_command`/`inspect_command` when present. `recovery` gives task/seq/revision, workspace, snapshot,
pending calls and the free-read route. Historical details remain available through free `read`
fragments; do not infer missing values from a deferred handle.
`schema` is generated from the parser's field table. `expected_seq` rejects stale submissions.
A single-event submit's `seq` identifies its own committed event, not any later concurrent writer.
Refresh next to observe later facts; successful receipt refresh may use a newer snapshot.
For check, it is rechecked when recording the first invocation; the batch retains its initial target and
checks sequence before subsequent calls. Earlier observations remain if later work conflicts.

## Bounded responses and free context reads

Every CLI JSON response fits 24 KiB of UTF-8 including its newline and escaping. Small responses are
complete inline values. A response with `deferred: true` instead supplies a complete immutable
`document` handle, `task` scope, byte count, `control` fields, collection counts and available blocker,
snapshot or output refs. Treat it as a locator, not a truncated complete result. Check the original exit status;
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
SHA256 of the returned text or a task snapshot ref. Fragments authenticate the consumed blocks and
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
For deferred delivery, read `/files`, `/bag_path`, `/receipt_path` and `/instructions_path` before giving
the user those links. A single-file delivery also exposes `/artifact_path`; multi-member delivery always
uses `/files`. The bag root is a standard BagIt directory; its `data/` contains the formal members.

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
An optional `--spec <file>` carries goal, criteria, assumptions and required delivery roles. Each criterion
has `id`, `description`, `checker`, `parameters`, `origin`, `required`, `basis`, `scope` and optional
`target`. Scopes are `content` (digest-based, filename independent), `member` (a named member path with its
complete descriptor) and `collection` (the full snapshot or an explicit path subset). A content target may
be one digest or a list; a member target is one canonical relative path; a collection target is an optional
path list. Use `origin: user` for explicit requirements; derived criteria remain revisable. The runner's
asset-validation criteria use `origin: policy` and cannot be weakened by a task strategy.
The defaults are provisional: relevant content (semantic collection) and nonempty bytes (mechanical
collection). A task created without explicit criteria cannot complete until `revise` refines the agreement
for the actual task. Supplied null/wrong types fail before task creation; valid assumptions are stored in
the created event at revision 1. Python callers pass these fields via `Workshop.start(request, spec={...})`.
`required_roles` lists stable role ids that every formal snapshot must cover. Adapt criteria and roles to
the real deliverable. Available checkers are `semantic`, `nonempty`, `json`, `contains`.
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
{"op":"report","call":"RETURNED_CALL_ID","text":"Actual deliverable","path":"report.md"}
```

This returns an observed output descriptor with `ref`, `path`, `bytes` and `media_type`. Publish the
complete member list rather than one content reference:

```json
{"op":"publish","members":[
  {"ref":"CONTENT_REFERENCE","path":"report.md","bytes":1234,"media_type":"text/markdown","role":"report"},
  {"ref":"DATA_REFERENCE","path":"data/table.csv","bytes":456,"media_type":"text/csv","role":"data"}
]}
```

A single file is simply a one-member snapshot. Every member must be an observed output or an explicit
existing snapshot member; byte counts and stored content are verified inside the task transaction. Paths
are canonical NFC relative paths with `/`, portable across platforms, unique under case folding and free of
file/directory conflicts. Roles are stable machine ids; every `required_roles` entry must be covered.
After interruption, `next` can suggest `publish` with one `publish_candidate`; inspect the task for
alternatives. For real files created by host tools, put them in the `workspace` returned by `next`, then invoke
`file.capture` with a relative path. Raw bytes are retained without decoding.

For several workspace files, prefer the recorded combination:

```sh
python <skill-directory>/scripts/fairy.py --home HOME prepare-delivery TASK --members plan.json
```

```json
{"members":[
  {"path":"report.md","role":"report","media_type":"text/markdown"},
  {"path":"data/table.csv","role":"data","media_type":"text/csv"}
]}
```

`prepare-delivery` records the complete member plan and per-member progress before publishing, captures each
member (reusing an exact recorded output when possible), publishes the complete snapshot and runs applicable
mechanical checks as separate recorded actions. It is resumable, not an atomic external operation: on
interruption, `next` returns action `prepare_delivery` with the full plan; a remaining-only retry still
resumes the recorded plan, which cannot be silently changed. It does not create semantic passes and does
not close the task. Required roles must cover the agreement; paths are canonical, collision-free and
portable.

Registered calls use `{"op":"invoke","capability":"NAME","parameters":{}}`.
Look up the accepted value contract through `capabilities --name NAME`. Invalid values are rejected
before invocation or budget charge. Asset search uses the local LanceDB BM25/ICU + vector weighted-RRF projection;
default 8, maximum 200, optional `cursor`, `scope`/`kind`. Results include the source generation, fixed model profile
and table version. An empty query browses active heads. A missing/stale projection or model returns
`search_not_ready` with the offending `stage` and a recovery route: `assets prepare` (download when absent,
SHA-256 verify six fixed files, no index, no inference) or `assets search --refresh` (same preparation plus
projection rebuild). An explicit refresh on an empty active library returns `projection.state=empty` with
the preparation result; ordinary search passes the fixed local directory and never downloads. Reading an adopted asset pins its exact version and exposes structured applicability,
dependencies and invalidation.
Read large inputs with bounded `content.read` fragments.

Run `{"op":"check"}` for mechanical criteria, then semantic reviews:

```json
{"op":"review","criterion":"goal","verdict":"pass","basis":"Explain the concrete comparison with the goal","evidence":["CONTENT_REFERENCE"]}
```

Add `"target":"CONTENT_REFERENCE"` or `"target":"data/table.csv"` when a criterion has multiple current
targets; collection criteria usually have one snapshot target. Use `fail` or `unknown` when appropriate.
Close with `{"op":"close","outcome":"complete"}`.
The close response keeps the operation identity (`task`, committed `seq`, `outcome`) and adds `delivery`.
A validated delivery carries the exported revision/seq/snapshot, paths, files and verification depth/time;
export failure carries `state=failed`, `committed=true`, `committed_seq`, `selection`/`selected_seq` and
`target` for the frozen export snapshot actually selected (`unknown`/null when selection did not complete),
the typed error and `recovery.command = deliver TASK`. SQLite and other storage failures during export use
the same envelope rather than a context-free generic error. Export failure never retracts the committed
close/fact; do not retry the effect, close, report, feedback or learning decision. Rejected transactions
carry `details.committed=false`; a COMMIT whose outcome cannot be confirmed carries `committed="unknown"`.
A failed write handler carries `effect_state="unknown"` for the external effect, not commit certainty.
An invoke failure keeps `task`, `call`, `operation`, `known_seq` (last confirmed seq) and `attempted_seq`
(the invocation event that may exist) plus `recovery.command = inspect TASK --history`. Unknown or rejected
invocations must be inspected before any retry; the handler may not have run, and a lost commit acknowledgment
does not authorize replay. A delivery failure after validated staging, including a native `OSError` from a
rename, post-publication check or lock release, retains `task`/`completed`/`published` and `quarantined` when
present plus `recovery = deliver TASK`; a lock-release failure does not turn a published result into an
unidentified generic failure.
Reviews bind the agreement revision, criterion fingerprint, checker contract, scope and exact target.
Semantic reviews bind the current snapshot. A new snapshot does not inherit semantic or collection-level
judgments; pure content mechanical observations may be reused when criterion, checker contract,
parameters, content and agreement revision are unchanged. Unreplaced failures for the current agreement
remain visible and require a grounded current check or an explicit semantic `replaces: [REVIEW_EVENT_ID]`.
Mechanical reviews link a successful recorded `content.check` or `snapshot.check` call and its exact checked
target, checker, parameters, verdict and basis. Custom check handlers must return this witness as
`checked`; contradictory or missing evidence cannot become a review.
Other outcomes are `partial`, `failed`, `cancelled`. Delivery builds a standard BagIt 1.0 directory with an
explicit `BagIt-Version: 1.0` header under `deliveries/<task>/<seq>/`: `data/` holds every formal member,
with `bagit.txt`, a SHA256 payload manifest, tag manifests, `bag-info.txt`, `receipt.json` and a concise
`README.txt`. Existing bags are checked against the task/revision/seq, snapshot, receipt and member digests.
Generation uses the vendored BagIt
wheel and performs full byte validation, never fast validation. An existing same-seq directory is revalidated
and returned without overwriting; late facts create a new seq directory and leave the old delivery intact.
`deliver <task> [--expected-seq S]` can regenerate or revalidate that export; a stale expected seq is a
conflict. `deliver <task> --repair --expected-seq S` builds and fully validates a replacement first,
quarantines an invalid derived directory without deleting it, and publishes; path-safety refusals use
`unsafe_delivery` and are never moved or followed. A repair failure after quarantine or publication
reports `completed`, `published` and the quarantine identity, so the host can recover without claiming the
old state was untouched. `inspect <task> --history` shows events.
Invocation budget limits new calls. Existing reports, answers, publication and semantic review remain
available at zero budget; required mechanical checks still need a registered call. Follow current issues.
Resource policy defaults are a warning at 128 calls and a final limit at 1024; the W05 calibration froze
these engineering values. `start --resources FILE` accepts work_calls and warning_calls, with positive
integer values and warning no larger than the limit. Omitted warning is min(128, work_calls). `content.read`
and `asset.read` are free context operations; CLI document reads and capability-catalog lookups are free.
Model requests, `asset.search`, checks, writes and captures remain counted. The start spec may also fix
adopted `governance` asset refs or a `governance_scope`; `governance --scope personal|team` lists adopted
constraint assets with structured applicability/dependencies/invalidation. Those refs must be read
before complete. `todos` lists unresolved deferred learning decisions across tasks without a task id.
The task records the effective policy and fingerprint once. `next`/`inspect` expose resources and warning;
changing the startup file or revising task requirements cannot expand that task's fixed allowance.
No cumulative question limit applies; keep one pending question and ask only consequential unresolved choices.

CLI SQLite runtime failures return nonzero `storage_failed`, a safe message, and `sqlite_code`/`sqlite_name`
when available. Preserve the store and inspect state before retrying. Version refusal remains `version`.
Invocations contain contract_ref. Read one historical definition through `inspect TASK --contract REF`;
ordinary inspect/receipts retain references without injecting full schemas. Adapter authors read
[tool contracts](tools.md); schemas and imported asset documents do not execute code.

If a pending writer has a pinned reconciler, inspect that definition, then use the read capability with
exactly `{call: ORIGINAL_ID}`. The runner derives confirmation from a genuine final observation, without
a separate status declaration or accept-proof command. The read uses ordinary permission and budget.
Do not repeat the writer after confirmation. Publish the appropriate confirmed member list and check the
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
explicit audit/backup/restore through the [operation guide](operation.md).
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
