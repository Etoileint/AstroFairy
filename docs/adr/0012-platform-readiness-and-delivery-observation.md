# ADR-0012: Platform-independent locks, explicit preparation and observed delivery

Date: 2026-11-08. Status: W1–W5 implemented; the first independent W6 round required rework (STD01–STD06, SPEC01–SPEC04, GAP01). The rework is returned for independent re-verification; maintainer acceptance and publication remain pending.

Inputs and requirements: [scope](../repairs/2026-11-platform-readiness-delivery/scope.md).
Baseline experiments and primary authorities: [supply](../repairs/2026-11-platform-readiness-delivery/supply.md)
and [source catalog](../repairs/2026-11-platform-readiness-delivery/sources.json).
This decision supersedes the affected current interface assumptions only after acceptance and implementation;
historical outcomes, reviews and release evidence retain their original baseline.

## 1. Derivation and responsibilities

A supported installation requires an environment-selected dependency closure with installable artifacts.
A usable search requires dependencies, verified model files and a current projection; each is a distinct fact.
Accepted content, a closed task and a locally validated export are also distinct facts.
An event sequence identifies recorded work, not the existence or continued validity of an external directory.
Historical receipt assessment and applicability under the currently installed checker registry are distinct inputs.

The selected structure retains the existing event authority and rebuildable projections:

| Responsibility | Owner |
|---|---|
| Dependency selection and environment forks | Pinned upstream uv universal resolver |
| Dependency policy, official provenance and consumer generation | One development lock orchestrator; data-driven profiles |
| Model preparation and model-cache verification | Search preparation service, shared by public entrypoints |
| Pure task scheduling and content acceptance | State/kernel; no filesystem or network observation |
| Export build, probe, validation and explicit repair | Delivery adapter |
| Composition of recorded state and export observations | Runtime and stage packet |
| Protocol serialization and recovery metadata | CLI/presentation adapters, without admitting work |

No new daemon, queue, vector database, generic workflow engine or task event for each export is required.
The existing LanceDB/E5 and vendored BagIt implementations remain the relevant mature implementations.

## 2. Dependency locking

### Selected mechanism

Replace both handwritten closure generators with one policy-driven development entrypoint backed by
`uv pip compile --universal --python-version 3.12 --generate-hashes --only-binary :all:`.
The Python lower bound comes from project metadata, not a duplicated constant; the example is the current bound.
Use a pinned tool from the existing development-tool SSOT, explicit official index configuration,
an approved cache, no interpreter auto-download and no ambient constraints/configuration or source-build fallback.
Universal solving preserves environment markers and can select different versions for different branches.

Profiles declare root-input locations, output locks and provenance locations. Core roots remain in
`pyproject.toml`; search roots are the directly used or explicitly profile-pinned stack in
`dev/search-requirements.in` (LanceDB, FastEmbed, ONNX Runtime, tokenizers, numpy and huggingface_hub).
Transitive resolution belongs to the resolver. An intentional transitive constraint must have a recorded reason,
not be mistaken for the entire dependency inventory. First implementation must review every version/hash delta;
the repair is not authorization for an unrelated dependency upgrade campaign.

Keep hash-locked pip requirements as the installed skill's consumption format. Conditional branches and
version alternatives remain explicit; do not flatten them to an unconditional name-to-version dictionary.
The existing offline BagIt wheel has its own verified build provenance; retain that channel rather than
substituting a different public artifact with the same package version.

`update` is an explicit resolving/network operation. It records tool identity, effective policy, input hashes,
resolved lock hashes and the authoritative artifact/metadata provenance. `check` is an offline consistency
operation over committed inputs, frozen locks and official snapshots, using upstream packaging APIs for
requirements, markers and versions. It must not silently resolve against today's index or claim an offline
manifest check proves all platform installations. A small closed-profile reader is a format adapter, not a solver;
unsupported generated syntax fails closed. Native fresh installation plus `pip check` establishes the tested closure.

The orchestrator rejects unknown profiles, missing pins/provenance, unapproved source URLs, missing hashes,
root/lock drift and outputs outside declared paths. The recorded tool identity includes the digest of the
actual uv executable resolved by the selected isolated interpreter through uv's own `find_uv_bin` contract,
not by guessing a neighboring file; update refuses when that binary or its digest cannot be established,
and check rejects a missing or malformed recorded digest. All newly resolved branch packages enter the source catalog.
Generated dependency diagnostics describe their actual scope and preserve markers; metadata availability is
not an import, ABI or inference test. Two old closure algorithms are removed, not retained as fallbacks.

### Alternatives

| Alternative | Decision and reason |
|---|---|
| Add two unconditional Windows pins only | Rejected: leaves host-dependent resolution and the same future omission mechanism |
| Grow an in-house universal resolver over a platform matrix | Rejected: duplicates solving and marker semantics, and cannot enumerate arbitrary future forks |
| uv universal compile with pip hash-lock output | Selected: mature resolver and existing secure installation route, with explicit native validation |
| uv.lock project migration | Valid mature option, not selected: would also reorganize project groups/build metadata beyond the needed contract |
| PEP751 pylock + native pylock installer | Valid standard option, not selected here: would change the runtime bootstrap/installer chain; a second canonical lock plus custom exporter adds an unnecessary semantic boundary |

PEP751 and packaging's mature pylock parser were examined; the offline fixture also successfully generated a
standard pylock. This decision uses a documented upstream output format and pip's official hash-checking contract.
It does not claim pip requirements are PEP751, or implement a private substitute for that standard.

## 3. Search preparation and observations

### Entry points

`assets prepare` checks the selected search dependencies, explicitly prepares the fixed model revision and
verifies every declared consumed model file. It works without adopted assets. It neither builds a projection
nor executes inference. `assets search --refresh` composes that same preparation operation and projection refresh;
it is a useful combined operation, not a second preparation implementation or an obsolete-name alias.

The manifest must first be audited against the actual fixed-version tokenizer/embedding consumers, not merely
checked for agreement with another copy of the same incomplete list. The baseline FastEmbed0.9.1 consumes
`tokenizer_config.json` and can consume `config.json` and `special_tokens_map.json` in addition to the three
previously hashed files. All six exist at the fixed revision. Record exact presence and hashes for all six;
obtain the three additional JSON bodies directly from that revision and extend the authority snapshot/generator
and consumer-discovery check. Optional consumer behavior must have a fixed presence/absence policy; an undeclared
configuration that changes tokenization is not allowed to become an invisible input. Dependency upgrades reopen
this consumption audit. The profile fingerprint changes with the file manifest, invalidating old projections
through the existing profile check rather than a migration.

Every explicit prepare/verify performs a new streamed verification at the advertised depth. It must bypass or
invalidate `_verified_dir` historical success; an in-process second request after file mutation cannot reuse the
old success. A currently loaded model and a currently valid on-disk cache are distinct observations. Ordinary
already-loaded inference does not gain a full-file scan on every query. Hugging Face's standard internal
cache links remain supported within the separately approved canonical cache root and fixed-revision content
checks; do not apply the delivery no-link tree policy indiscriminately to that upstream cache layout.

Preparation runs outside SQLite transactions. Serialize competing preparations for the same model cache with
the existing native file-lock mechanism; report bounded busy/failure honestly. Acquire projection work only
after preparation, then read a fresh asset generation. No network operation holds the main database transaction.
Preserve fixed revision/hash checks and explicit local-only tokenizer/embedding consumption.

An empty active library after explicit refresh returns preparation identity and `projection.state=empty` with
zero assets/chunks. Do not invent a nonempty index or return a global `ready=true`. An ordinary empty-library
query still returns an empty result without downloading/loading a model. Unadopted/retired-only libraries are
also empty active libraries. Search responses with explicit refresh retain its preparation result even if the
query/filter matches nothing. Normal nonempty semantic search may perform necessary local embedding inference.

### Diagnostic contract

Replace the ambiguous aggregate search boolean with typed observations:

| Field | Meaning and permitted evidence |
|---|---|
| `dependencies` | Expected direct/profile versions and observed distribution metadata; import/ABI not inferred |
| `model` | `absent`, `present_unverified`, `verified` or `invalid`; identity, verification depth and observation time when checked |
| `projection` | `not_checked`, `empty`, `missing`, `stale`, `profile_mismatch`, `unavailable` or `current`; bind generation/profile/table version when read |
| `recovery` | Explicit next command and whether it downloads, verifies bytes, builds an index or runs inference |

Default `doctor` remains non-mutating and cheap: dependency metadata, approved cache-location/file-presence
observations only. It neither opens/creates the task database nor hashes model weights; projection is
`not_checked`. Its top-level core readiness is distinct from optional search observations. A model cache that
merely exists is never `verified`. The preparation response supplies byte verification, not inference success.
An explicit `doctor --verify-search` can stream-verify cached model bytes without download or inference;
it does not assert projection readiness. Query/refresh paths perform their own current projection checks.
Verification records are observations at a time, not permanent assertions against subsequent external mutation.

No persistent global readiness flag, hidden model prewarm or automatic provider/model substitution is introduced.

## 4. BagIt representation boundary

Use the upstream library to parse and fully validate BagIt. Convert each library-exposed manifest key from
the actual host path flavor to a canonical POSIX relative identity before payload/tag classification or set
comparison. Convert tagmanifest filenames relative to the exact bag root using the same boundary. Tests inject
Windows path flavor without pretending that a Linux Path object is a native Windows Path.

Reject absolute/drive/UNC paths, escaping traversal and distinct exposed keys that collide after conversion.
Preserve upstream manifest validation and the project's canonical member-path policy; do not reinterpret
backslashes globally in user paths or rewrite raw manifests to make verification pass. Check the bag root and
tree for forbidden symlinks, then compare canonical payload/tag sets. Continue verifying the task/revision/seq,
snapshot, exact receipt, every member length/digest and authoritative blob. A library-valid replacement package
can still fail the authority check. No fast validation or relaxed hash check is accepted.

This boundary cannot recover distinctions already erased by upstream parsing. Do not claim an independent
raw-manifest parser or exhaustive raw-syntax alias detection; canonical exposed identities plus upstream
validation and the authoritative member/receipt comparison are the enforced contract.

Containment covers every component from the approved, canonical home through deliveries/task/seq, staging,
lock and quarantine paths, not only the bag subtree. Before any creation or move, inspect the existing
ancestors without following redirects. On Windows explicitly reject junctions and unsupported reparse points
as well as symlinks, using Python's documented path/stat APIs and symbolic constants. Recheck under the native
delivery lock before publication/repair. Unsafe ancestors, roots or descendants are structured refusals; do
not move the redirect itself or touch its external target. Shared layout checks do not become a new in-house
filesystem sandbox: arbitrary concurrent hostile filesystem mutation and power-loss durability remain outside
the stated guarantee. Known redirects and accidental out-of-home writes are covered and must fail closed.

Once the replacement staging is fully validated, one progress boundary covers safety rechecks, both renames,
post-publication verification, result construction and lock release. Native `OSError` and `FairyError`
failures after that point use the same structured envelope: `task`, `completed`, `published`, any existing
`quarantined` identity and a `deliver` recovery command. A lock-release failure must not mask an earlier
error, and must not turn an already published result into an unidentified generic failure.

## 5. Task closure and export lifecycle

### Separate the facts

`State.complete()` remains content/evidence acceptance. Public packet names expose this as
`acceptance.complete`, with its current-runtime assessment identity; it does not certify a local bag or rewrite
historical acceptance. `State.next_action()` reports `closed` for historical
outcomes, keeping execution-conflict precedence. It never reads directories and never derives `delivered`
from outcome. The runtime composes the pure action with a cheap delivery observation for the same frozen seq.

| Local observation at current seq | Stage action | Meaning |
|---|---|---|
| No target directory | `deliver` | Build from recorded facts |
| Target exists but has not been fully checked in this operation | `verify_delivery` | Candidate only; invoke deliver to fully validate |
| Root is an observed unsafe object or inaccessible | `inspect_delivery` | Structured refusal and explicit corrective route |
| Current execution conflict | `inspect_conflict` | Retain the conflict action; expose export observation separately |

`verify_delivery` is a packet action whose command is the ordinary `deliver`; it is not another partial verifier.
A previous process's success never causes next to assert present validity. Cheap probes do not open/hash payload
files or create directories/locks. Successful `deliver` returns `delivery.state=validated` with the exported
task/revision/seq/snapshot, verification depth/time and paths. This is evidence for that operation, not an
indefinite or globally current delivered flag. The host completes its delivery step on that result; it must not
loop back through next demanding a permanent validated state.

### Composition and errors

After a fact commits, one shared runtime path attempts to export a closed task when the originating operation
requires a refreshed receipt. Route close, late model reports, late feedback, late tool observations and learning
decisions through it. A learning decision may advance seq and create a child; those facts must not be repeated
because export failed. Successful responses retain the operation's own `committed_seq` and any child/call identity,
separate from `delivery.seq` if another writer has advanced the stream before export selection.

Export failure returns a bounded structured result containing the original typed error, `committed=true`,
the operation identity/committed seq, the selected export target when known, and a `deliver` recovery command.
It must not turn a recorded tool result into a failed/unknown tool execution, or encourage retrying the effect,
close, report, feedback or learn. Pre-commit failure is `committed=false`; unknown commit outcome is explicitly
unknown. External effect uncertainty is reported separately as `effect_state`, never as commit certainty.
Command exit status remains nonzero for the export failure. Large-response and response-export failure
envelopes preserve these recovery controls within the established byte limit and without raw exception text.

Transaction certainty is produced at the store boundary for BEGIN, native statement-body and COMMIT failures:
a known rollback is `committed=false`, an unconfirmable outcome is `committed="unknown"`, and the original
statement/COMMIT error remains the cause even when a later rollback fails. The runtime adds operation identity
and, for invoke admission/invocation failures, the known call id, last confirmed seq, attempted seq, stage and
an `inspect TASK --history` recovery action. An unconfirmed invocation is neither reported committed nor
replayed; the handler may not have run.

No new `delivery_exported` event is appended to the task stream: doing so would itself change the seq used by
the bag and receipt. Export observations are derived from actual files and returned operation evidence; they
are not a competing authoritative task outcome. A durable operational export journal can be considered separately
if a real consumer requires it; it is not needed to resume correctly from authoritative facts plus local files.

### Snapshot and concurrency

Select and verify one event snapshot in a short database read transaction. Build a historical receipt projection
from that snapshot, without injecting the current capability registry. Export outside the database transaction under the existing per-task native delivery lock;
immutable blobs supply the bytes. Read a fresh state only as a separate observation, never blend it into the
frozen receipt. `deliver --expected-seq S` checks the selected state before work; it is not a claim that writers
cannot append afterward. Without the precondition, deliver selects the latest observed state.

Different seq exports remain different directories. Same-seq concurrent exporters serialize and validate/reuse
the same bag. A result explicitly bound to S may become old immediately; next subsequently targets the newly
observed seq. This preserves late facts and avoids holding SQLite write transactions during large file hashing.
The old architecture prose suggesting export is serialized with all event writers must be corrected to this
actual, tested snapshot contract; no global filesystem/database transaction is claimed.

### Deterministic receipt inputs

The current `_inspection()` mixes event-derived facts and current checker applicability, so it is not a valid
receipt authority. Replace that reuse with a dedicated historical projection. Its complete semantic inputs are
the verified events through S, their recorded agreement/resource policy/contracts/content references and
observations, and receipt projection format2. Preserve invocation/target/result grounding against the recorded
checker contract; do not disable evidence checks. Do not include current catalog descriptions, installed checker
definitions, wall-clock observation timestamps, model-cache state or live readiness in the receipt.

Recorded reviews, failures and historical assessment are reduced using the recorded checker identities.
Budget presentation that depends on current accounting implementation is excluded or defined by the frozen
projection-format rules; recorded policy and original calls remain available. Next/inspect retain a separate
current-runtime assessment with the current checker-contract identity, so changed checkers can invalidate current
acceptance/adoption without rewriting what was historically observed. Closed outcomes remain historical facts.

Same-seq receipt bytes must be identical across restart and changes to the installed checker registry.
Golden event-to-receipt fixtures enforce this contract. A semantic projection-rule change requires a new receipt
projection format and an explicit design decision, not silent same-version output drift. Format2 is distinct from
BagIt1.0 and document archive1. Unsupported derived receipt formats are identified as such, not mislabeled as
corrupt authoritative facts; ordinary deliver refuses them and explicit derived-file repair can preserve and
regenerate them without introducing an old-format reader or a task-store migration.

### Missing, invalid and restored exports

Missing exports regenerate normally. Existing valid same-seq bags are reused after full validation.
Existing invalid/unsafe exports are refused by ordinary deliver, with a reason and explicit repair route;
unsafe objects remain a refusal rather than permission to follow or move them.
`deliver --repair --expected-seq S` is an explicit operation on derived files within the approved home:
validate authoritative inputs and build/fully validate a replacement staging bag first; then, under the same
delivery lock, move a safely identified invalid old directory to a unique quarantine sibling and publish the
replacement at the canonical seq path. Never delete quarantine, follow a symlink, overwrite a valid bag,
quarantine an authoritative database, or treat a store-integrity error as permission to replace files.

The two directory renames are not one cross-platform atomic replacement. An interruption can leave the
canonical target absent; next then offers deliver, and facts plus quarantine remain available. Publication
uses the existing same-filesystem rename discipline; durable-power-loss guarantees require platform evidence
and are not inferred from rename. Failure details retain any completed quarantine action and recovery identity.

Restore excludes exported deliveries by contract, so a restored closed task naturally offers deliver.
Historical distributed files remain historical; learning/late facts do not silently overwrite them. No migration,
old packet alias, old boolean fallback or automatic source-data cleanup is added.

## 6. Compatibility, growth and alternatives

This changes response/action semantics: advance protocol10 to11 and stage packet1 to2; receipt projection becomes2.
There are no new authoritative task events or
database tables in the selected design, so store10 and document format1 remain appropriate; change them only if
implementation demonstrates an actual persistent-format change and returns that decision for review.

The general mechanisms depend on declared profiles, exact identities and explicit observations. More dependency
branches or task types do not add kernel-specific policies. The lock orchestrator replaces two algorithms;
the delivery observer earns its place by isolating filesystem knowledge from State. New public commands are
distinct operations, not compatibility aliases.

| Delivery alternative | Decision |
|---|---|
| Roll back closed/late facts when file export fails | Reject: loses or misrepresents committed observations; database and filesystem are not one transaction |
| Catch errors and still return delivered | Reject: preserves the misleading state and gives no trustworthy recovery |
| Add a task-stream export-success event/boolean | Reject: seq feedback loop and stale success after deletion/restore |
| Hash every bag on every next/doctor | Reject: turns navigation into unbounded file work and still cannot promise validity after the check |
| Pure closed state + explicit local probe + full deliver observation | Select: accurate, resumable, cheap navigation, existing byte-level safety |
| Separate durable projection job service | Not selected: no current requirement justifies scheduling infrastructure for a locally reconstructable export |

For preparation, compare moving one early-return line, a separate unconnected model loader, and the selected
shared prepare service plus a compositional refresh. Only the latter aligns all entrypoints while preserving
cheap ordinary empty queries. For paths, compare blanket slash replacement/relaxed validation with the selected
host-aware canonical boundary; only the boundary preserves both representation and authority checks.

## 7. Verification and acceptance boundary

The [validation matrix](../repairs/2026-11-platform-readiness-delivery/validation.md) defines requirement coverage,
faults, concurrency, recovery, native-platform and packaging checks. The
[implementation plan](../repairs/2026-11-platform-readiness-delivery/plan.md) defines ordered work and handoff.
No implementation, raw cold-model download, Windows native execution or product acceptance is implied by this ADR.
