# ADR-0003: Semantic review identity, observed checks and closed effects

Date: 2026-10-30. Status: implemented and independently verified within F01; maintainer acceptance pending.

## Scope and authorization

The maintainer authorized root-cause repairs and optimization within AstroFairy after the initial review.
This slice addresses R16-D01, R05-D01, R05-D02, R14-D01 and the R10-D01 store admission boundary needed
for a clean format replacement. It does not implement arbitrary external-call
reconciliation, account security, remote synchronization or unrelated findings. User effort and the
four-step skill entry remain unchanged. The cooperative host/trusted handler boundary remains explicit.

FDP C routes the changed semantic contracts through A. At P1–P5, executor=root,
verifier=f01_independent_verifier, arbiter=maintainer. Authorization covers this repair scope and routine
implementation decisions; independent verification does not substitute for final user acceptance.

## P1: Responsibilities and invariants

1. A registered test file must contribute collected TestCases, or the gate must refuse the suite.
   The collected cases are frozen into a native standard-library suite and executed once per isolated surface.
2. A review's semantic target is task-agreement revision plus immutable content ref. Publication event
   sequence is provenance/concurrency information; republishing or returning to identical bytes cannot
   erase a failure for the same semantic target.
3. A bookkeeping-only revision does not create a new agreement revision. Actual agreement changes and
   forwarded user answers invalidate prior checks. Explicit reassessment preserves predecessor ids/basis.
4. A mechanical judgment must reference a successful recorded content.check call. Both the recorded
   invocation and the handler's checked witness must equal the current ref, checker and parameters;
   verdict and basis must equal the observation. Missing/malformed/mismatched evidence cannot promote
   a review or supersede a predecessor. The checker may be wrong about reality; the runner must still
   reject an observable identity contradiction.
5. Active review selection and replacement use only eligible judgments for that target. Invalid old
   mechanical evidence cannot retire a valid predecessor or earn current completion credit.
6. Task permissions and capability declarations share one closed effect vocabulary: reason/read/write.
   Write includes sending, deletion, publication and any other external mutation. Unknown categories
   are refused before invocation; exceptions or post-handler result-validation failures for a write
   remain unknown and block blind retry. A lying handler is outside this cooperative boundary.

## P2: Authorities and evidence

The actual cached original identities and reading scopes are retained with the repair evidence under
`.evaluation/repairs/F01/`. Use the official [Python unittest discovery contract](https://docs.python.org/3.12/library/unittest.html#test-discovery)
and [unittest suites](https://docs.python.org/3.12/library/unittest.html#unittest.TestSuite): the framework
performs discovery/execution; project policy audits its result. W3C [PROV-DM](https://www.w3.org/TR/prov-dm/)
distinguishes generated entities, activities and responsibility; it motivates explicit links, not a claim
that local hashes certify tool truth. The versioned [MCP tool specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
separates input/output contracts and errors; tool effect annotations are hints, so they do not replace
this runner's enforced permission vocabulary. These references are scoped precedents, not blanket
PROV/MCP conformance claims. The four original counterexamples and positive controls remain frozen.

## P3: Mechanism and alternatives

### Collected tests

Keep unittest. Put the discovery pattern in governance.toml, use that same value for expected owner-local
files and TestLoader.discover, collect the actual TestCases and map their module files back to expected
files, then freeze those cases into unittest.TestSuite and run with TextTestRunner. Only native TestSuite
containers and module-owned TestCase subclasses are supported; custom suite execution and FunctionTestCase
are refused. Empty suites, lost modules, duplicate case ids, foreign/unregistered modules and loader errors
fail. Helpers use non-test names. A load_tests hook cannot silently
discard a registered test. Each surface still runs in a fresh Python process.

Only adding __init__.py checks or narrowing Ruff ignores leaves custom loading/zero-case holes.
Switching frameworks does not itself prove admission/collection consistency. A small policy wrapper
around the existing framework earns its place; it does not implement discovery, assertion or execution.

### Review identity

Select reviews by revision+ref, not publication sequence. Retain artifact_seq in raw records and keep
the conservative during-check seq/revision race guard. Returning A→B→A restores A's eligible judgments.
Canonical equality of revised specifications prevents a no-op revise event from incrementing revision.
Every forwarded answer increments revision. Do not carry judgments across genuinely changed agreements;
do not prohibit legitimate new
artifacts or explicit reassessment.

### Mechanical evidence

The built-in checker returns `checked: {ref, checker, parameters}` with verdict/basis. A derived mechanical
review adds its source `call` id. Kernel admission and active selection validate that witness against
the durable invocation, current criterion and observation. Durable invoked parameters are the authority,
so mutating a handler argument cannot mutate the expected identity. Scope/concurrency checks remain.

A ref-only comparison leaves wrong checker/parameter variants; comparing a mutable input dictionary
leaves mutation variants. Adding a tool label without the recorded source call leaves provenance
unverifiable. Reusing the existing event/call ledger avoids a second evidence store or state machine.

### Effects

Define one validator and vocabulary in the protocol contract. Capability construction and task-start
scope consume it; invocation/admission defend the same boundary. The effect class describes permission,
not the tool's business name. New tools use these classes without adding kernel branches. Rejecting
unsupported categories is preferable to guessing whether each new verb mutates external state.

## P4: Adversarial validation plan

- Test discovery: nested/no-init failure, load_tests omission, zero cases, foreign suite, loader errors,
  skipped-but-collected tests, valid nested cases and normal existing surfaces.
- Identity: fail/pass conflict; same ref republish; A→B→A; no-op revise; real agreement change; true byte
  repair; explicit replacement; reopening; candidate-validation adoption cannot exploit republishing.
- Observation: wrong ref/checker/parameters; missing/empty/malformed witness/verdict/basis; mutable
  argument changes; source call linkage; no predecessor replacement on invalid output; check-time race.
- Effects: every unsupported declaration/scope rejected before handler/charge; read/reason failures
  vs write failures, including invalid return data after an actual effect; unknown blocks repeats.
- Run the canonical full gate and independent reproduction plus composition controls; no new user
  steps, no budget increases or relocation tricks, no suppressed hooks or weakened checks.

## P5: Completion and development format replacement

The maintainer explicitly excludes backward compatibility during development. Store format 2 admits only
the new contracts. Before any DDL, an existing database must have exactly the supported metadata version;
old, unknown or malformed stores are refused without modification. New stores initialize format 2.
There is no migration, fallback, old-event projection or dual review path. Use a fresh home for development
tasks; refusal does not delete old data. This also eliminates the revision-number collision identified in
the first independent design review. Frozen review snapshots remain historical evidence, not live-code gates.

Completion requires the original failures to be refused, meaningful positive controls to succeed,
independent design/implementation evidence and an updated live repair ledger. Unrelated findings and
user acceptance remain pending. No commit, push or external Issue is part of this slice.

## Verification record

P1–P3 passed independent design review after the maintainer excluded compatibility. P4 passed independent
reproduction, positive controls, races and composition checks; P5 technical records are completed in the
[F01 report](../repairs/F01-evidence-and-admission.md). Both execution channels ran 55 runtime and 10 development
tests and the canonical gates. The later default-effect deduplication has a separate independent identity
and behavior addendum. This is bounded technical verification, not a claim of overall product acceptance.
