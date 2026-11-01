# ADR-0011: Verified replay, record lifetime and recoverable state

Date: 2026-10-31. Status: implemented; P02 independently technically verified; maintainer/product acceptance separate.

## P1: Scope, actors and assertions

F09 addresses work-program P02. Executor=root, verifier=f09_independent_verifier,
final arbiter=maintainer at every gate. FDP B independently re-establishes the costs and recovery gaps;
conceptual repair proceeds through A P1–P5. Only AstroFairy is writable; no commit/publication, destructive
cleanup, old-store reader, migration or compatibility branch is authorized by this work.

1. Preserve complete event-chain verification in each admitted transaction; remove only redundant
   post-commit reads whose answers already follow from that transaction. No persistent State cache,
   unchecked checkpoint, SQLite-data-version heuristic or weaker historical-corruption detection.
2. A single-event submit returns its own committed sequence, not a later unrelated writer's seq.
   Report/feedback closedness is known in that transaction. Invoke's observed/asset-used events cannot
   change the captured closedness; a later close exports the already committed observation itself.
   Preserve handler-outside-transaction concurrency, unknown writes, late facts and current receipts.
3. Define separate lifetimes for authoritative events/blobs/assets, derived document blocks, exported
   receipts/artifacts, and uncaptured workspace/external state. Retirement changes selection only;
   old pins remain readable. No automatic expiry, GC or implicit deletion. No finite disk guarantee.
4. Provide explicit administrative state audit, backup verification, backup and restore. Use native
   SQLite online backup, not copying live database files. Copy main first and document archive later;
   retain all archive blocks, including handles issued outside main DB. Do not infer liveness from
   scanning only learning inputs. A backup is a consistent main snapshot with a later document superset,
   not an atomic two-database timestamp.
5. New learning inputs register their document locator as a typed `source_document` value alongside
   the existing content ref. Validate exact locator/content identity and audit its owner-bound root.
   This removes opaque-JSON root inference for enforced references. Protocol/store becomes 7;
   the document-block format remains 1. No format-6 reader or migration.
6. Restore only into a fresh destination, retain partial failures explicitly, validate before declaring
   success, recreate task workspace directories and regenerate deliveries on demand. Never overwrite a
   live home, discard pending/unknown calls, invoke a capability or automatically retry an effect.
7. Audit and backup are explicit maintenance, potentially expensive. Measure hot replay, byte work,
   retained bytes and retirement behavior; no universal latency, long-term usefulness or power-loss proof.

## P2: Authorities and alternatives

Exact raw originals, URL/SHA and actual read ranges live in `.evaluation/repairs/F09/{primary,independent}/`.

- [SQLite online backup](https://www.sqlite.org/backup.html) and
  [Python 3.12 Connection.backup](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup)
  provide consistent database images with concurrent writers and incremental steps. Use progress/deadline
  handling and closed, standalone destination databases; no custom SQLite file-copy/locking protocol.
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html) define stable read snapshots and
  write serialization. [Corruption guidance](https://www.sqlite.org/howtocorrupt.html) motivates avoiding
  live-file copying, aliases, unknown journal handling and manually copying WAL fragments.
- [Microsoft Event Sourcing](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
  describes immutable events, snapshots and their complexity. Snapshots can accelerate rehydration, but
  a stored hash proves bytes, not that those bytes are the correct reduction of the original events.
  Introducing an unverified State checkpoint would change the present corruption/admission contract.
  Retain strict full replay and reduce duplicated reads; do not deploy an enterprise event service
  for a local skill. A measured per-task cost remains visible for explicit future design decisions.
- VACUUM/VACUUM INTO can compact free pages or create one database image; neither defines which
  evidence may be deleted or makes two databases/external files one snapshot. Backups retained outside
  the live home address recovery; they do not cap retention or establish off-machine redundancy.

Compare in-memory verified caches, persistent derived State, immutable event-page proofs, and strict
replay. Cache invalidation and semantic trust are real costs; no candidate may silently trade away the
existing full-chain validation to claim speed. The selected minimal replay change introduces no cache.

## P3: Mechanisms and interfaces

### Replay and sequence

`submit` has exactly one appended event after its admitted pre-state, except invoke/check/learn branches
which already dispatch separately and close which returns delivery. Reuse that pre-state's closedness
for report/feedback and return pre-state.seq+1. In invoke, reuse the state captured in the observation
transaction to decide whether a closed receipt needs refresh. Keep all actual admission and confirmation
rechecks across handler execution. No reducer change or State alias/cache is needed.

### Lifetime policy

- Main DB: events, original blobs, contracts, asset versions and asset events are authoritative records.
  Preserve them, including obsolete versions and late facts, until a separately authorized deletion design.
- Document DB: derived immutable blocks remain retained because issued handles can be external roots.
  All blocks are backed up. Unreferenced blocks are a measured cost; no pretend complete reachability index.
- Deliveries/receipts: regenerable from captured facts via deliver. Already distributed copies and paths
  inside historical documents retain their historical meaning; restore does not rewrite immutable bytes.
- Workspace files not yet captured, installed code/environments, credentials and external tool/service
  state are excluded. This is recorded-state backup, not a whole-machine or arbitrary work-in-progress backup.
  Restored pending/unknown attempts require normal investigation, not retry based on backup presence.
- An agent handles maintenance paths and ids. Members acquire no new form-filling responsibilities.
  Capacity and backup cadence are explicit deployment choices; no background daemon or deletion schedule.

### Recovery adapter and immutable bundle

New `_maintenance.py` is an administrative storage adapter. It cannot admit task operations, change event
outcomes, execute tools or adopt assets. CLI routes before Workshop construction:
`audit-state`, `backup --out NEW_DIRECTORY`, `verify-backup DIRECTORY`, and
`restore DIRECTORY --out NEW_HOME`. Ordinary task paths gain no backup/full-archive audit work.

A bundle directory contains fixed `workshop.sqlite3`, optional `documents.sqlite3`, and a bounded,
canonical format-1 `manifest.json` with each file's byte count and streamed SHA256, store version,
exclusion declaration and creation time. Paths are fixed, never selected by manifest input.
New private destination directories are created exclusively; no overwrite/merging of existing paths.
Only successful validation permits writing the completion manifest. Failures may leave a private partial
bundle without a manifest; preserve it for inspection, never call it complete or silently delete it.

Use native backup on a read-only source connection, first main DB, then the current document archive.
Each target connection closes and yields a standalone image (normalize target journal mode to DELETE).
The main snapshot may name only documents published before its referenced event committed. Because the
archive has no deletion, a later document snapshot contains those roots even with concurrent appenders.
A missing document archive is allowed only if the captured main snapshot has no typed document roots.
Extra roots/blocks are allowed and retained. Concurrent external deletion/replacement of source files
or hostile direct DB edits violates the cooperative-storage assumption and is not solved by ordering.

Read-only audit reuses Store.events/get and the kernel replay over read-only connections, checks SQLite
integrity/foreign keys, every blob identity, valid task ids, every stored node identity and all document
roots. Reuse the document adapter's scalar/key/edge verifier in a bulk archive traversal with a shared
per-audit visited set; do not reconstruct/checksum each overlapping root separately. This visits all
stored blocks and validates each consumed edge/role even when its child was previously visited.
Typed locator metadata is checked through the existing authenticated root/selection path; aggregate
full-archive verification then covers its entire graph. No global unchecked cache is introduced, and
ordinary selected reads retain their 128-node cache limit. Individual audit-document retains its
full canonical digest. Whole-archive audit does not claim a separate flat digest for every root or
strict linear work for arbitrary key layouts. It validates the following enforced-reference registry:

| Record | Enforced local paths |
|---|---|
| created | inputs[*].ref; typed inputs[*].source_document as below |
| invoked model request | refs[*] |
| invoked registered tool | contract_ref, optional reconciler.contract_ref |
| observed | outputs[*].ref; successful native result.outputs; final native reconciliation.result.outputs |
| published | ref |
| reviewed | ref, evidence[*] |
| asset_used | ref, which must also be a registered asset |
| asset package | ref/blob metadata equality; base points to same scope/name and strictly older version |
| asset event | ref; candidate/retired have no validation task; trial/stable bind validation task below |

Revised/asked/answered/feedback/closed have no enforced blob refs. Unknown event kinds fail audit. Tool
parameters and arbitrary result fields are opaque; text/URLs and package evidence source strings remain
declared provenance, not guessed enforceable references. Native reconciliation validation reuses its
pure existing binding/result-schema checks; it does not run a reconciler or reaccept the task.

Typed source_document inputs must equal the content locator and the audited root metadata (owner,
bytes and seq). Source locators are explicit retention links, not new content authority. Audit compares
asset table scope/name/version/kind/summary/tags/base with its exact package blob. Each adopted asset
event must link a task whose input and published artifact are this package, whose historical outcome
is complete and whose protected criteria match validation_criteria. Do not recompute current complete()
to invalidate a historical adoption because of later conflicting observations. This checks stored
structural binding, not truth of semantic fitness or a renewed adoption decision. Asset state vocabulary
comes from one shared library declaration. Aggregate counts are bounded; history is not echoed.

Verify manifests strictly: exact format/fields/filenames, counts/digests and no symlink/nonregular inputs.
Hash files before and after read-only audit to detect accidental concurrent change; no authenticity or
protection against an adversary able to rewrite both manifest and files is claimed. Restore copies only
these verified files into its newly created private home, checks copied hashes, audits there, then creates
workspace directories. A private `restore.pending` marker is created before any database file is copied
and removed only after validation and directory creation finish. Store admission refuses that marker
before DDL, so an interrupted restore cannot accidentally look like an ordinary usable home. The marker
is this operation's own transient control, not a retained record or native lock file; failure leaves it
in place for inspection. Existing backups/source homes remain untouched. SQLite images and manifest use
private modes, explicit UTF-8, flushed files and atomic manifest writing. Standard fsync is not a tested
power-failure or hardware durability guarantee. No automatic lock file or copied live WAL is restored.

### Failure and growth boundaries

Timeout/busy, corruption, missing references, invalid manifests, unsupported versions and filesystem
errors fail safely. No raw SQL, source values or exception text becomes public diagnostics.
No incomplete bundle or failed restore counts as successful recovery. Rollbacks, old source files,
recovery ids, task event counts and effects remain unchanged. New format-7 homes only.

Strict replay still scales with history; complete native projections inherently grow. Larger work can
be split into explicitly linked follow-up tasks without discarding previous evidence, but no automatic
split or semantic summary is introduced. Inventory and measurements explain data growth; they cannot
prove indefinite affordability or choose a universal backup cadence for all deployments.

## P4: Independent requirements

- Compare pre/post event-load counts, bytes and measured task sizes. Corrupt historical data must still
  refuse the next admitted action. Test concurrent commits and exact reply seq, late report/feedback,
  closed receipt refresh, invocation/check/reconciler paths and existing full regressions.
- Back up under real concurrent main/document writers; deterministic old-doc-first failure versus new
  main-first success; absence/presence of archive; retain externally issued old/global documents.
- Restore in a fresh home; read/reconstruct/audit old docs, regenerate identical delivery, keep pending
  effects unknown, inspect/adopt/retire assets with historical pins. No handlers run during maintenance.
- Missing/corrupt main blob, typed locator/root, archive node, asset base/task, malformed manifest,
  duplicate/unknown fields, symlink/path injection, input mutation, partial copy, busy/deadline and existing
  destination all refuse. Show readonly source bytes/event rows unchanged, including unsupported metadata.
- Full checks, original budgets/entry/history identities, source/ZIP/installed-wheel admin commands and
  final seals. Distinguish local synthetic fixtures from actual members, native hosts or hardware failures.

## P5: Closure

P1–P3, the restore-marker/bulk-audit impact gates and P4 independently passed. The audit reference
registry, ambiguous exclusion wording and dangling-archive admission were corrected and revalidated.
The [F09 record](../repairs/F09-record-lifetime-and-state-recovery.md) retains phase-specific identities,
raw failures, all limits, metrics and six-field termination. Only P02 is technically verified within
its declared retention/recovery policy and measured scope.
Strict replay and retention remain growing costs, not hidden solved-by-snapshot claims. P03–P07 and
maintainer acceptance remain open. Six-field termination and resource/evidence limits belong in F09.

Backup preserves captured record bytes exactly, including any credentials already present in them.
The environment/credential exclusion concerns uncaptured external files; it does not promise filtering
or redaction of captured events, blobs or documents. Treat backups with the same access control as records.
