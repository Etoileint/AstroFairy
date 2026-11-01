# ADR-0008: Authoritative confirmation of an uncertain attempt

Date: 2026-10-31. Status: implemented; independent P1–P4 technical verification passed;
P5 recorded in the [F06 report](../repairs/F06-authoritative-attempt-confirmation.md).
Maintainer acceptance remains separate.

## P1: Scope and invariants

F06 addresses R02-D01. R02-D02 remains a separate whole-response consumption design, including
criteria, pending parameters and all other variable fields, not just answered events. Executor=root,
verifier=f06_independent_verifier, final arbiter=maintainer at P1–P5. FDP B re-established both current
boundaries; the selected conceptual repair proceeds through A under the existing implementation authority.
Only AstroFairy is writable; no commit, push, publication, migration or compatibility path is authorized.

1. Support same-task continuation only for write capabilities explicitly configured with a trusted,
   read-only reconciler able to prove that this exact attempt has finished with a reproducible result.
   Absence, an in-flight operation, a file that happens to exist, a human risk decision or a model's
   assertion cannot confirm the attempt. Unsupported/ambiguous cases retain honest partial/failed/cancelled exits.
2. Preserve the writer's durable attempt, parameters, contract and original observations. A confirmation
   is a different tool's recorded fact; it never rewrites the original handler's unknown/pending result as ok.
3. Freeze the authorized verifier name and definition ref before the write. The actual read invocation
   must carry the target before observation and match that exact authority. Ordinary read permission,
   matching witness text or a newly replaced same-name contract grants no confirmation authority.
4. Use the existing registered-call pipeline and ordinary read permission/budget. No second executor,
   user-supplied verdict command, automatic write retry, hidden service or human bookkeeping step.
5. Conflicting positive evidence remains sticky, including after closure or later matching/unknown
   observations. Current conflict blocks complete and new adoption. Historical closure is retained;
   current next/inspect/delivery/receipt disclose the dispute. This batch has no conflict-clearing override.
6. Factual confirmation may concern an older task revision; quality checks still bind the current
   agreement and actual artifact. No automatic revocation of already exported files or adopted assets.

## P2: Authorities and alternatives

Official originals, SHA256 identities, selected read scopes and source-bound probes are retained under
`.evaluation/repairs/F06/primary/` and `independent/`. Sources are scoped precedents, not certifications.

- [AWS Builders' Library: safe retries](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/):
  lost responses do not establish failure; resource existence does not identify its creating attempt;
  parameter hashes cannot identify business intent; caller tokens, atomic provider operations, late
  arrivals and retention windows require explicit contracts.
- [Microsoft Event Sourcing](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing):
  immutable source events and current projections have distinct duties; compensating/correcting facts
  preserve history. Snapshots optimize replay and do not replace the event stream.
- [Temporal Continue-As-New](https://docs.temporal.io/workflow-execution/continue-as-new):
  mature workflow platforms explicitly bound execution histories. This motivates a separate growth
  decision; it does not confer external-effect certainty or justify introducing that platform here.

Compared alternatives: the existing conservative stop is safe but cannot supply the selected same-task
confirmation capability. A model/human status override loses fact provenance. A private verifier callback
would still need invocation identity, schema, permission, budget, persistence and historical authority;
reuse the existing registered read invocation instead. A full durable workflow platform adds deployment
and scheduling obligations while still needing domain-safe effect correlation. Automatic retries and
negative absence-based closure require stronger external idempotency/quiescence contracts and are excluded.

An extra reconciled event was considered, then removed from the design: the premarked native invocation
and its validated observed result already contain every fact. Resolution and conflict are recomputable
projections, so no redundant second acceptance event or host accept/reject command is needed.

## P3: Contracts and mechanism

### Explicit authority before effects

Capability accepts an optional reconciler name only for write capabilities and exposes it in its
definition. Before recording the write, the runner validates that the named capability exists, is read,
and accepts the canonical input {call: ATTEMPT_ID}. Store its complete definition blob and freeze
{name, contract_ref} in the writer's invoked record. Definition hashes identify declarations, not code.

Context.call_id identifies the actual committed invocation and is supplied before handler execution.
It is None for preflight/non-invocation contexts. It is an attempt identity, not a promise of business
idempotency, provider deduplication or cross-task exactly-once execution. The adapter must arrange and
verify any provider token/transaction needed for its operation.

Within a task containing a pinned writer declaration for a reconciler name, calling that capability is
a dedicated verification operation: require exactly {call: target}, that target's declared name/ref,
read effect and a prior writer attempt. Reject missing/wrong targets, extra parameters, stale verifier
contracts or changed effects before executing. Do not silently downgrade these calls to ordinary reads.
Capture the target marker in the read's invoked record before executing its handler. Qualification
survives original late ok and prior confirmation; later contradictory evidence must still be recognized.

No registered writer is recoverable by inference. Built-in file writers do not acquire this authority
from a path/hash match. An adapter must explicitly implement authoritative attempt correlation.

### Positive, full-result confirmation profile

A marked verifier returns the ordinary tool result plus a reconciliation object on positive confirmation:

```json
{
  "outputs": [],
  "reconciliation": {
    "target": {"call": "ATTEMPT_ID", "operation": "ORIGINAL_OPERATION", "contract_ref": "WRITER_REF"},
    "final": true,
    "result": {"outputs": []},
    "basis": "Authoritative completed attempt receipt and its correlation"
  }
}
```

The runner validates the target against the captured durable binding, not mutable callback inputs.
The reconstructed full result must satisfy the shared tool-result rules and the original writer's
frozen outputSchema; each referenced blob must exist and pass its digest check. Its output descriptors
must occur in the verifier's observed outputs with sufficient multiplicity. Extra verifier evidence
outputs are allowed; they are evidence, not automatically the deliverable.

The identity for comparing full results is canonical JSON, including exact descriptor order, names,
media types, multiplicity and all additional result fields. A mere ref set, reordered list or compatible
but different transient result is insufficient. Adapters opting in must provide a reproducible final
result. This is deliberately narrower than arbitrary semantic equivalence or effect-only confirmation.

Nonfinal/unknown replies do not resolve the writer. A malformed positive proof fails the read observation
safely. No source field supplied by a host turns into tool truth. There is no public force-status or
accept-proof command. Independent artifact/quality checks remain necessary, and no deferred handler
follow-up code is replayed from the reconstructed result.

Do not copy every normal result into a new blob: ordinary results currently have no 16MiB aggregate
limit. Confirmation identifies the existing observed full result by a derived digest and source event;
that digest is not advertised as a blob reference. The exact proof remains available in its raw event.

### Replay, conflicts and retry

Replay recognizes confirmation only from a marked successful native read observation whose actual
invocation name/ref/parameters and proof target match the original writer's authority. Derive a separate
confirmation summary pointing to its source call/event and canonical result digest; preserve original
status/result. Later unknown does not negate a valid positive fact.

Remember positive native writer results and authorized confirmations by digest during replay, including
facts preceding the first confirmation. Any different positive result for that attempt produces a sticky
conflict with source-event identities. A→B→A and A→B→unknown remain disputed. New matching evidence cannot
quietly replace a contradictory fact. No conflict-clearing path is included; investigate and use honest
termination/follow-up. Extra assertions from unmarked reads are not automatically promoted to authority.

An uncertain writer is effectively settled only with an authorized positive confirmation and no conflict;
normal successful writers continue to work. Same-operation retry remains blocked for any confirmed
attempt or conflicted attempt, even after a matching late ok. Confirmation never authorizes repeat effects.
The parameter digest remains a local guard, not a business idempotency key.

Current execution conflicts enter complete, next action, inspect and export projections. A closed
complete is a historical decision; disputed current evidence is disclosed separately and never presented
as an unqualified current completion guarantee. Closed tasks are not reopened for new execution.

### Durable facts and honest delivery projection

Commit the native observation first. If the task is closed, refresh its receipt afterward; projection
failure cannot roll back the observation. Derive all export fields from one task snapshot and serialize
each export with event writers in its own SQLite transaction, avoiding stale exports overwriting newer
ones. Receipt/return seq identifies that snapshot. The SQLite event commit and filesystem export are
not a cross-resource transaction: a file may lag, an export may fail, and previously distributed copies
cannot be retracted. Inspect/next are current authority; deliver can regenerate a projection.

Development store/protocol format 4 replaces 3 without migration or dual readers. Permission, budget,
question and quality policies retain their responsibilities. Native verifier trust and external finality
are adapter obligations, not a sandbox or proof against malicious developer code.

## P4: Independent validation obligations

- Real positive unknown and interrupted-pending writers, authoritative attempt token, matching outputs,
  real same-task continuation, artifact checks, reopening and immutable original unknown/pending evidence.
- Missing/wrong read capability, effect, target parameters, verifier contract, frozen writer schema,
  result fields, output descriptors/order/multiplicity, missing/corrupt blob and source call origin refuse.
- Input/context mutation cannot change committed identity/binding; role-qualified extra/missing input
  cannot bypass automatic recognition. Same-name replacement and registration removal preserve history.
- Nonfinal/absence/exception remain unresolved; no automatic write execution or retry permission;
  ordinary result above 16MiB is not newly rejected by a duplicate-blob requirement.
- Actual concurrent original handler and verification: matching late ok, late unknown, conflicting late
  ok before/after close, A→B→A/unknown, later contradictory verifier and exhausted read budget.
- User revision change permits original-attempt verification while invalidating old quality reviews.
  New asset adoption after conflict rejects; no retrospective global revocation claim.
- Observation commit survives export failure; regenerated/parallel exports use one monotonic snapshot
  and display dispute. Current next/inspect/receipt cannot hide a conflict behind historical complete.
- Prior repair composition, old-format refusal, canonical development gates, final source and actual
  distribution identities. R02-D02 remains open regardless of this batch passing.

## P5: Completion boundary

Only the selected opt-in confirmation capability may close R02-D01 after independent technical P4.
No arbitrary external recovery, negative-proof retry, exactly-once service guarantee, whole-packet bound,
constant replay cost, retrospective asset revocation, native host certification or real-user benefit is
claimed. Results, remaining obligations and termination declaration belong in the F06 report/ledger.
