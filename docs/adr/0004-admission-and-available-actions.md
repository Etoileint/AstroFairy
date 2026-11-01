# ADR-0004: Transactional admission, initial agreement and available actions

Date: 2026-10-30. Status: implemented and independently technically verified within F02; maintainer acceptance pending.

## P1: Scope, authority and invariants

F02 repairs R04-D01–D03 and R03-D01. The maintainer authorized root-cause implementation and explicitly
excludes development compatibility. Executor=root, verifier=f02_independent_verifier, arbiter=maintainer
at P1–P5. FDP C routes these runtime contract changes through A conservatively; this does not retroactively
resolve the historical review's conceptual/writing classification dispute. No sibling repository changes,
commits, pushes, external Issues or global installs are authorized here.

1. A supplied expected_seq compares the source task at a serialized admission point before any admitted
   action. Ordinary commands, invocation, checks and learning use one sequence predicate inside a shared
   runtime transaction boundary. The field remains optional, not an idempotency token.
2. Checks freeze the initial agreement revision, publication sequence, content and candidates. First
   invocation rechecks the initial sequence in the transaction that records invoked. Subsequent calls use
   the preceding iteration's observed/reviewed sequence. Target changes stop promotion and later calls.
   Empty candidate sets still validate admission. External handlers never run inside a SQLite transaction.
3. Learning reads a closed source, its summary, and creates the child in one serialized transaction.
   Source history is not changed. Same-current-sequence repeated requests may create distinct children;
   the child's immutable input identifies the source task and snapshot seq. No single-use or dedup promise.
4. All initial agreement fields validate before task/workspace/blob creation. Missing fields select
   defaults; supplied null, false, zero or wrong container types do not. Accepted assumptions belong to
   created at revision 1. Task metadata and attachment blobs commit together. CLI configuration validation
   precedes opening Workshop; a Python caller may already have initialized its home before calling start.
5. SQLite runtime errors at the CLI boundary return nonzero machine-readable storage_failed with safe
   diagnostic identifiers. Version refusal remains version. No SQL, paths, values or raw exception text
   are exposed by that mapping; no automatic deletion, rebuild or retry is introduced.
6. Budget limits new counted calls. Scheduling preserves free report, answer, publication and semantic
   review paths, while the existing complete gate and required mechanical checks remain mandatory.
   The packet's state and forwarded answers derive from one event snapshot, even if the source changes later.

## P2: Authoritative precedents and actual evidence

Reuse identity-checked official originals retained for R04; the F02 evidence records actual reading scopes.
[SQLite transactions](https://www.sqlite.org/lang_transaction.html) and
[isolation](https://www.sqlite.org/isolation.html) provide the actual single-writer/IMMEDIATE/snapshot mechanism.
[Python sqlite3](https://docs.python.org/3.12/library/sqlite3.html#exceptions) defines Error and the runtime
sqlite_errorcode/sqlite_errorname attributes. [Microsoft's event sourcing guidance](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
is the scoped precedent for events, projections and optimistic concurrency; it does not guarantee arbitrary
side effects exactly once. [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) provide a
strict/extra-forbid validation alternative. [SCXML transition selection](https://www.w3.org/TR/2015/REC-scxml-20150901/#SelectingTransitions)
is a comparison for enabled-action ordering, not a claim that this runner implements SCXML.

The independent verifier reproduced four defect groups and positive controls on the pre-F02 implementation.
F01 already seals non-SQLite-file version refusal; R04-D03's remaining counterexample uses supported
metadata and malformed events columns to produce a real OperationalError. Historical reports remain frozen.

## P3: Mechanism and alternatives

### Admission and creation

A small runtime _admitted context combines BEGIN IMMEDIATE, replay and the kernel's sequence predicate.
It composes existing Store transactions; it does not implement a new lock or transaction engine.
Ordinary submit, invoke and learning consume this same boundary. Private task creation participates in
its caller's transaction; public start/validation/learning own their respective transaction explicitly.
This permits coherent source-to-child creation without nested transactions or savepoint infrastructure.

For checks, the first call's invoked is the linearization point when there are candidates. The initial
read transaction alone is not permission to execute later. After each observation, a transaction verifies
the original target, records a valid review where appropriate, and obtains the sequence for the next call.
Non-target events such as feedback arriving during a handler may be absorbed into that transaction;
updates arriving between iterations and the next invoked conflict with its expected sequence. This is
not an atomic whole-batch promise: completed observations remain when later work is refused.

Preflight-only checks leave the race. Holding a transaction around external execution blocks unrelated
work and cannot make external effects transactional. A dispatcher spanning every command and handler is
unnecessary. A new learning_started event was considered and rejected: source mutation/deduplication is
not needed for snapshot admission, and the child summary already records source identity and sequence.

### Initial specification

A single pure contract function normalizes request plus optional goal/criteria/assumptions, budget and
effects using the existing validators. Workshop.start accepts request plus spec mapping; old goal/criteria
keyword forms are removed rather than supported as aliases. All creation paths use the same function.
CLI validates with that function before opening the store, and the Python API validates at its own boundary.

Configured strict Pydantic with forbidden extras could enforce these fields. For this fixed, small surface,
existing strict JSON and value validators provide the required rejection behavior without adding a runtime
installation requirement to portable skills. This is no general schema engine: extension tool contracts
remain a separately tracked responsibility. Merely changing truthiness branches or patching CLI after
creation would leave multiple authorities and partially initialized tasks.

Input reads and blob insertion occur within the creation transaction after configuration validation, so
a later missing attachment rolls back earlier inserted blobs. No handler is invoked there. Filesystem
directory creation and SQLite are not a distributed transaction; arbitrary OS/crash recovery is outside
this batch. In particular, this is not a promise to remove every possible empty directory after a disk fault.

### Error envelope

Catch sqlite3.Error at the CLI operation boundary; retain FairyError precedence. Emit storage_failed,
a fixed safe inspect-before-retry message, SQLite code/name when supplied by SQLite, and nonzero exit.
Missing attributes are null. Do not spread conversion through Store, kernel and adapters or catch all
exceptions. Argparse usage errors keep their native contract. Ordinary Python API callers retain SQLite
exceptions. Tool-execution results and programmer errors are not relabeled as successful operations.

### Scheduling table

State derives next_action from its existing facts; runtime renders the packet. No new lifecycle state,
budget, background process or user step is introduced. Runtime reads one event list for both replay and
user_updates; a second unlocked read could mix old seq/revision with a newer answer in the same packet.

| Condition, in order | Suggested action |
|---|---|
| Closed | delivered |
| Complete | close |
| Pending question | wait_for_answer |
| Pending/unknown calls | resolve_pending |
| No artifact, known output exists | publish |
| No artifact/output, budget available | produce |
| No artifact/output, no budget | close_failed |
| Artifact, no budget, required issues only semantic | review |
| Artifact, no budget, required mechanical issue remains | close_partial |
| Artifact, budget available | review or repair according to existing evidence |

Known outputs are one State projection used by publication and scheduling. next exposes one
publish_candidate; inspect provides alternatives. This is a candidate, not an automatic quality selection.
Optional-only issues cannot block completion. A semantic failure is not erased: review can reassess with
evidence and explicit replacement, or the host can choose partial delivery. Unknown tool effects remain
unresolved, not promises of eventual completion; their reconciliation stays R02-D01.

## P4: Validation obligations

- Sequence: stale/zero/current/absent expected for ordinary, invoke, check and learn; real concurrent writers;
  first-invocation race; empty candidates; target changes between calls; feedback during a call; no transaction
  held during handler; stale admission creates no calls, children, workspaces or blobs.
- Source-to-child: same snapshot in summary, source unchanged, repeated current requests explicitly permitted;
  transaction failure rolls back child events/blobs; closed-source requirement retained.
- Start: missing/default vs explicit null/false/zero/wrong types, unknown fields and mixed lists; valid
  assumptions in created at revision 1; CLI bad config creates no home; Python creates no task/blob/workspace;
  missing later attachment rolls back earlier capture; validation/learning still create valid tasks.
- Errors: actual structural, locking, readonly and integrity SQLite errors; safe/null diagnostics, no raw
  exception leakage, nonzero JSON; version/FairyError/native usage controls; no destructive recovery.
- Scheduling: question/pending/unknown, budget 0/positive, no artifact with/without output, pure semantic
  review and explicit reassessment, required mechanical deficit, optional-only issues, closed/complete;
  repeated next is read-only, answer interleaving cannot mix snapshots, and new calls still enforce the same budget.
- Run canonical gates, independent reproduction and composition with F01 review/effect safeguards; rebuild
  portable distribution and verify the changed path from the resulting runtime.

## P5: Completion conditions and limits

Only these four findings may move to verified after independent technical revalidation. No historical
finding is silently rewritten. Maintainer acceptance, remaining confirmed issues, unknown-effect recovery,
context growth and long-term user outcomes stay pending. Keep technical results and termination record in
the F02 report and the current status in the repair ledger. No compatibility, migration or legacy branch.

## Verification record

P1–P3 passed independent design review. P4 passed independent before/after matrices, real writer/source
interleavings, failure injection, F01 composition controls and actual portable-launcher checks. The later
single-event-snapshot rendering change passed local design/implementation revalidation and a newly built
portable runtime. Root ran 75 runtime and 10 development tests plus the canonical gates; this is separate
from the verifier's own probes, not a claim that the verifier ran that entire suite.
P5 technical records and remaining obligations are in the [F02 report](../repairs/F02-admission-and-available-actions.md).
