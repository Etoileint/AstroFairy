# Architecture

AstroFairy organizes delegated work into usable delivery with inspectable evidence.
The user provides a task request and occasional consequential choices. The host owns semantic reasoning.

## Responsibilities

The control loop admits a proposed action, records its start, invokes a capability, and records observations.
`_kernel.py` owns admission and replay rules; `_store.py` owns durable content and events;
`_contracts.py` owns command parsing; `_runtime.py` composes the loop and host work packets.
These four files have reported size metrics and reviewed responsibilities, without a physical-line hard cap.
Library and capability implementations are workshop assets
and adapters; they do not gain permission to change task scope or terminal state.
`_presentation.py` is a transport adapter beside the CLI: it bounds serialized responses and provides
lossless document access through the derived `_documents.py` block archive. These adapters cannot append
task events or admit operations; no control responsibility
is moved out of the four budgeted files. Native Python values remain full objects.

Task agreement, action proposal, execution result and review are separate protocol objects.
Model reports remain model reports. Mechanical reviews are produced through the actual checker path.
Requirements distinguish explicit user constraints, immutable runtime policy and derived assumptions.
Completion requires all necessary current checks to pass and no unresolved call or question.
Initial goal, criteria and assumptions share one strict normalizer. The CLI validates configuration before
opening the store; task creation persists the complete initial agreement at revision 1. Attachment blobs
and task events share a transaction. A Python caller may already have initialized its Workshop home.

## Persistence and revision

SQLite transactions serialize event updates with optimistic sequence checks. Original bytes are captured
in content-addressed blobs. The event chain is the task history; current state and reports are projections.
One runtime admission boundary checks expected_seq inside the transaction. Checks freeze their initial
target and recheck sequence when recording each invoked call; handlers run outside transactions. A batch
may retain completed observations when later work conflicts. Non-target feedback during a handler may be
included at that iteration's close; it cannot change the frozen review target.

Content is SHA256-addressed bytes. A member is `{ref, path, bytes, media_type, role}` with a canonical
NFC relative path; the same bytes may appear under distinct paths. A snapshot is the versioned format-1
member list sorted by path with its own SHA256 identity; role and other acceptance-relevant fields
participate, while order changes do not create a new snapshot. Publication accepts the full member list
and validates every entry against an observed output or explicit seed/snapshot authority in one
transaction. Delivery writes every formal member under its relative path.

Criteria declare `content`, `member` or `collection` scope. Content checks bind a digest and may be reused
when criterion, checker contract, parameters, content and agreement identity are unchanged. Member checks
bind the complete member descriptor. Collection checks bind the snapshot and selected paths; a new
snapshot does not inherit collection-level passes. Reviews bind the agreement revision, criterion
fingerprint, checker definition, scope and exact target. Semantic reviews bind the current snapshot.
A pass cannot silently erase a failure: unreplaced failures for the current agreement remain visible and
block required completion until a grounded current check or an explicit semantic reassessment replaces
them. Explicit reassessment retains predecessor ids, producer, rationale and evidence.
Mechanical judgments additionally link the recorded invocation and its observed target, checker, parameters,
verdict and basis. Admission and completion use the same evidence rule. Required delivery roles must be
covered by current members; a provisional default agreement cannot complete before model refinement.

Starts are committed before effects. A process interrupted during a call leaves it unresolved, rather than
asserting failure or retrying. Closure stops scheduling while retaining late reports and observations.
Capabilities and task permissions share the closed classes `reason`, `read`, `write`; sending and deletion
are writes. Unsupported classes are rejected before execution. A write exception, including invalid returned
data after execution, leaves an unknown result and blocks identical retries.
Exports are reproducible projections; a failed export can be regenerated from the store. Delivery uses the
vendored bagit wheel with an explicit BagIt 1.0 header and regenerated tag manifest: formal members stream
into `data/`, payload/tag manifests are generated, full byte validation runs in a private staging directory,
and publication is an atomic rename to a new task/seq directory. Existing same-seq bags are revalidated
against the authoritative task/revision/seq, snapshot member set, receipt and each member digest, so an
internally consistent replacement bag is rejected. They are reused, never overwritten; late facts create a
new seq directory. BagIt library calls are serialized against their process-wide cwd change. Local manifest
hashes prove byte consistency, not external authenticity or semantic quality.

Writes may explicitly pin a trusted read reconciler and its definition before effects. The committed
invocation id is supplied to handlers for attempt correlation. Within that task a pinned reconciler name
requires exactly its authorized call target; native marked observations alone can establish confirmation.
The full recovered result uses the original writer's schema and exact canonical identity. Confirmation
and sticky positive-result conflicts are projections of immutable invocation/observation facts, without
another acceptance command/event or overwriting the original handler result. No negative inference,
automatic retry or provider exactly-once guarantee follows.

Current execution integrity is separate from historical outcome. Conflicts block complete and future
adoption, survive later matching/unknown facts, and remain visible in next/inspect/delivery. Late facts
commit before a closed receipt is refreshed. Each export uses one snapshot and is serialized with event
writers in a separate transaction; projection failure cannot undo a fact. Snapshot seq exposes staleness;
old distributed files and adopted assets are not automatically revoked. Unsupported recovery remains explicit.

Development uses store format 10 and protocol 10. Existing unsupported or malformed store metadata is refused
before DDL. There are no migrations or compatibility branches; use a fresh approved home for new tasks.

Registered tools expose immutable JSON Schema value contracts. python-jsonschema performs validation;
the local static profile disallows foreign retrieval, dynamic binding and unknown/deprecated schema keywords.
Static input validation precedes admission; trusted non-effecting resource/business preflight follows
permission/budget checks but precedes invoked. Post-handler result validation cannot turn failed writes
into safe retries. Public corrective diagnostics are bounded; unexpected exception text is not forwarded.
Invocation records contain the exact definition ref. Current or historical definitions are read individually,
not embedded in every packet or receipt. Hash identity is not handler-code attestation.

The runtime uses locked upstream dependencies rather than a bespoke schema interpreter. Standard venv/pip
preparation happens once in an approved location, with all selected wheel hashes fixed from official PyPI
release snapshots. No launcher installs packages automatically. Missing dependencies remain diagnosable.
SQLite prerequisites are checked by in-memory materialized-CTE/window/callback/foreign-key controls using the
same connection setup as the store. Doctor reports the result; unsupported engines refuse before
persistent home/database mutation. This checks required capabilities, not storage durability.

## Workshop and learning

Methods, workflows, tools, cases, profiles and constraints grow outside the control protocol.
Lookup returns bounded metadata; relevant content is read on demand. A workflow gives instructions,
inputs, parameters and completion conditions to the host; it is not executable Python or a new core branch.
Repeated tasks, successful methods, failures, edits and feedback can drive maintenance.

Discovery projects active adopted heads (the latest trial/stable version per scope/name) into a local
LanceDB table. Chunks cover name, summary, tags, structured applicability, dependencies, invalidation,
inputs, parameters, workflow steps, body and evidence;
structure-aware splitting uses the fixed model tokenizer and a bounded token budget without silently
truncating the remainder. Retrieval fuses LanceDB BM25 with ICU segmentation and exact-vector E5-large results using
weighted RRF (full-text 2:1) over per-path asset ranks. The fixed profile records fusion weights,
model source/revision/file SHA256, tokenizer, prefixes, normalization,
field scope and backend version.

Each projection records `source_generation` (maximum asset-event sequence), a local epoch, the profile id
and the LanceDB table version. Index writes happen first; the pointer is committed in the main database
only after they finish. A query takes one short SQLite read snapshot for G, active heads and pointer,
requires the pointer G to equal G exactly and the profile/epoch to match, releases the transaction, then
opens a separate table handle and selects the recorded version. Filters use exact asset refs; candidates
and retired versions are excluded from ordinary discovery. Missing, stale, mismatched or unavailable
indexes return `search_not_ready` with the preparation route; they never become an empty success. The
explicit `assets search --refresh` preparation downloads the fixed revision with the locked SDK, verifies
every declared model file SHA256, and then uses the same fixed directory for the tokenizer and embeddings.
Ordinary search passes `local_files_only=True` and an explicit fixed directory; it does not download or
start another revision. The index is a rebuildable cache; SQLite asset events remain the authority. The agent
short list defaults to 8 and ordinary CLI pages to 50, both capped at 200; an opaque cursor binds the
query, scope, kind, source generation, profile, table and version. Empty queries browse active heads
without model execution. Fusion uses per-path asset ranks with weighted RRF (full-text 2:1), so adding
body text is measurable separately from metadata discovery.

Maintenance uses ordinary tasks. Adoption requires successful validation of the exact candidate package,
including an asset-fitness judgment. Changed bases reject stale adoption. Sharing transports an asset package,
never installs code, and requires local validation after import. Scope is a local namespace.
Retirement excludes an asset from active selection; immutable history supports inspection and new rollback proposals.
Learning freezes the source snapshot, creates its maintenance task and appends the linked source decision
in one main-database transaction. Its input identifies the source task and sequence before that decision;
the reply identifies the committed decision sequence. Either write failing rolls back the child, blobs
and source decision together; the separate document archive may retain unreferenced derived blocks.
Each delivery offers an explicit `maintain`, `defer` or `no_change` learning decision; unresolved deferrals
remain discoverable across tasks and sessions through `todos`, as well as the source's `next` packet.
Asset packages may declare structured applicability/dependencies/invalidation, which stay in the
package and enter the retrieval projection. A task agreement may fix adopted governance asset refs; those
assets are pinned by `asset.read` and remain independent of search top-k. A successful decision advances
the source sequence, so a retry with the old expected_seq conflicts. Requests without a precondition or
with a newly read sequence may create another maintenance task; expected_seq is not an idempotency token.

ResourcePolicy is a frozen typed contract. Its format, values and canonical SHA256 fingerprint are recorded
in the first task event and cannot be changed by revise. Default warning/final work-call counts are 128/1024;
the W05 resource calibration exercised normal repeated work and abnormal file/schema/lock/backup paths before
freezing them. They are not industry mandates or token/currency/time limits. CLI --resources loads a closed
JSON policy before creating a home; the Python entry accepts ResourcePolicy. next/inspect expose usage and
warning; deferred packets preserve the warning. The warning does not block work. Questions have no lifetime
quota; one pending question remains required. `content.read` and `asset.read` are free context operations, as
are CLI document reads and capability-catalog lookups; model requests, searches, mechanical checks, writes and
captures remain counted. Free calls are recorded but do not reduce `remaining_calls`.

All implementation budgets live in the frozen `Limits` dataclass (`_limits.py`) with a budget id, unit and
consumer per field. `schema` exports that manifest. It separates command JSON, semantic text, tool contracts,
schemas, response envelopes, content reads, search pages, content bytes, locks, backup deadlines and internal
document blocks; relaxing one does not relax permissions, evidence, integrity or exact-target checks.

Scheduling is a State projection. New-call budget does not remove free reporting, answers, publication or
semantic review. A full snapshot can be published after budget exhaustion; required mechanical checks still
need counted calls. Optional issues cannot prevent completion. Pending/unknown effects remain visible.
The packet's state and forwarded answers derive from the same event snapshot; it reports snapshot members,
role coverage, missing roles and unresolved failures.

All CLI JSON responses, including errors and fragment envelopes, fit 24 KiB including the final newline.
Oversized values become immutable owner-bound document handles with small control metadata and counts.
Free RFC 6901 selected fragments retain exact canonical JSON and advance until an explicit end. Selection
uses pinned python-json-pointer; its source-bearing exception text is never a public diagnostic. The
document commitment includes scope and typed blocks; it is not an execution witness or a replacement
for permissions. `selection` commits a typed subtree, not SHA256 of its canonical text. Free selected
reads authenticate consumed bytes/navigation only. `audit-document` checks every reachable block and
returns a separate full canonical-text digest; unread sibling damage may pass a selected read.
Post-effect projection failure preserves authoritative recovery identities and committed observations.

Learning captures a full source/history document in the source transaction and places only its locator
in the maintenance task. This removes the aggregate ordinary-blob ceiling without changing individual
content limits. Task events and the derived archive are separate transactions; a rolled-back child may
leave unreferenced blocks. Canonical typed/versioned SHA256 blocks share unchanged values and completed
collection prefixes across snapshots. Each block is at most 16 KiB, fanout is 16 and the per-read verified
cache is at most 128 nodes. Selected ranges skip authenticated spans and do not parse the entire source.
A snapshot still traverses its native input; early insertions can shift collection groups and rewrite
metadata. Full audit traverses the graph/content and may materialize a large scalar for canonical validation. These are
explicit costs, not universal logarithmic-update or bounded-memory claims.

Archive writers use the pinned native filelock for schema admission before normal SQLite transactions:
finite timeout, no soft fallback, stable private lock pathname. Readers do not acquire/create it.
Unknown/empty existing archives refuse without reinitialization. No SQLite aliases or hardlinks are used.
These mechanisms do not provide retention policy, replay checkpoints, bounded disk, host-context
compaction or universal latency. P02–P07 in the [work program](../repairs/work-program.md) retain the
separate lifecycle, actual-task/host/member, learning-benefit and overall-acceptance obligations.

Behavioral constraints distinguish applicability, failure consequences, enforcement and explanatory purpose.
Facts, profiles and transient task state remain separate. Size metrics inform responsibility review;
physical brevity is not a proof of permanent architectural completeness.

## Actual enforcement boundary

This is a cooperative host skill with a local runner, not a sandbox or independent hosted agent.
It enforces its own command protocol, registered operations, state transitions and review bindings.
It cannot prevent a host from bypassing the runner, lying about user input, editing its code/database,
or making unsupported semantic judgments. Hash chains are local tamper detection, not external attestation.
Filesystem guards protect ordinary path traversal; they are not race-proof isolation against a hostile host.
Invocation counts and content budgets are enforced locally; real model tokens and wall time remain host-managed.
Tool provenance means the runner invoked a registered handler, not that every handler is trustworthy.
These limits are part of the protocol's interpretation and must survive future integration changes.


## Record lifetime and recovery

The [record-lifetime decision](../adr/0011-record-lifetime-and-state-recovery.md) retains strict full
history verification at admission, removing only duplicate post-commit reads. Single-event replies
identify their own committed sequence. No persistent State cache weakens semantic or corruption checks.
`_maintenance.py` is an explicit administrative storage adapter: it audits records, uses native SQLite
backup and restores only a fresh home. It cannot admit operations, execute handlers or change outcomes.
Its reference registry checks captured inputs, published snapshot objects and every member ref, review
targets/evidence and native confirmations, tool contracts, used assets, package metadata/base/adoption
binding and typed learning source_document links. Arbitrary parameters/results and textual provenance are
not scanned as links.
Main-first/document-later backup is safe under append-only document publication before referenced events
commit; it preserves a document superset, not an atomic timestamp. Every stored block is checked with
shared traversal; individual text checksums remain a separate command. Unknown versions refuse.
Events, blobs, asset versions and document handles retain their evidence lifetime. Retirement only
changes selection. No GC or disk ceiling is implied; external handles prevent pretending current-task
reachability is a complete root set. Restore excludes uncaptured workspace/external/environment state,
keeps pending effects unresolved and blocks incomplete destinations with a marker before Store DDL.
P02 resource/capacity costs and the real-use acceptance obligations remain explicitly scoped.
