# ADR-0005: Declared and enforced tool contracts

Date: 2026-10-30. Status: implemented and independently technically verified within F03;
maintainer acceptance pending.

## P1: Scope and invariants

F03 repairs R06-D01: discoverable input-value contracts, pre-execution validation and useful failure feedback.
Executor=root, verifier=f03_independent_verifier, arbiter=maintainer at P1–P5. FDP C routes the changed
contract through A. The maintainer authorizes implementation inside AstroFairy, excludes development
compatibility and prioritizes mature mechanisms. No sibling changes, global installs, commits or publication.

1. Every registered tool has a valid name, effect, concise public description and one immutable input
   schema. The same schema that callers inspect drives actual validation. Optional output schemas use
   the same engine; a shared result envelope protects published output metadata.
2. Invalid static parameters never enter a handler, consume invocation budget, append events or store a
   tool-definition blob. A trusted non-effecting preflight may check distinct byte/resource/business
   preconditions inside admitted state, after sequence/permission/budget checks and before invoked.
3. A registered invocation records the immutable definition it actually used. Definition changes cannot
   authorize blind retry of an unresolved operation. Definition identity is provenance, not code attestation.
4. Explicit public errors retain bounded corrective information. Schema errors expose public schema
   locations/rules, not rejected values, dynamic instance keys or exception strings. Unexpected handler
   failures expose only a fixed safe diagnostic. Post-execution write failure remains unknown.
5. Summary discovery remains bounded; full schemas are read on demand. Tools, schemas and dependencies
   are workshop resources, not new task states or branches for individual business tools.
6. Dependency preparation is explicit, local and one-time. Missing dependencies can be diagnosed without
   opening the store. No launcher silently downloads code; the agent handles normal environment setup.

## P2: Authorities and alternatives

Actual official originals, selected reading scopes, release metadata and SHA256 identities are retained
under `.evaluation/repairs/F03/`. References are scoped precedents, not MCP certification or an upstream audit.

- [MCP Tools 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/server/tools): inputSchema,
  optional outputSchema, discovery, actionable execution errors; this runner remains a local skill.
- [JSON Schema Validation 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation): standard
  types/enums/bounds, integer's zero-fraction semantics, character lengths and format annotation/assertion.
- [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901): pointer escaping, UTF-8 URI fragments and canonical
  array indices. Independent probes found the selected reference library accepts Python-style indices.
  The local authoring profile rejects noncanonical integer-like tokens even for object members, validates
  fragment encoding/escaping, and safely projects resolver failures. Resolution stays with the library.
- [python-jsonschema validation](https://python-jsonschema.readthedocs.io/en/stable/validate/),
  [referencing](https://python-jsonschema.readthedocs.io/en/stable/referencing/): versioned validators,
  public resource/registry APIs and trusted-schema assumptions. Explicit Registry() is required: an
  independent experiment found validator defaults can otherwise retrieve remote references.
- [pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/),
  [Python venv](https://docs.python.org/3.12/library/venv.html): fully pinned/hash-checked binary installs
  and target-local environments; virtual environments are recreated, not transported between machines.

Compared candidates: callbacks plus separately handwritten descriptions leave two rule authorities;
Pydantic strict models provide useful validation but compiled dependencies still require preparation and
strict Python int semantics do not equal generated JSON Schema integer semantics for 2.0. Vendoring a
smaller validator adds upstream/license/update responsibility and a narrower draft or compiler/retrieval
surface. Complete python-jsonschema plus ordinary venv/pip has a smaller mechanism for this requirement.
The earlier stdlib-only choice was not a maintainer constraint and is cleanly replaced.

## P3: Mechanism

### Schema and registration

Use jsonschema 4.26.0 Draft202012Validator with explicit empty referencing.Registry. Pin the whole runtime
closure in pyproject.toml. No hand-built schema validator, remote resolver, coercion framework or vendored fork.
SchemaContract lives with existing protocol contracts; Capability holds private canonical schema bytes
and validator instances. Descriptor access returns copies; registration accepts only complete Capability
objects. Workshop.register validates names and refuses duplicate registration unless replacement is explicit;
capabilities is a read-only view. Old required/optional constructor forms are removed.

Use an explicit 2020-12 dialect, object root and explicit top-level additional/unevaluated-properties policy.
The local authoring profile rejects unknown schema keywords and unsupported dialect/vocabulary changes.
Allowed keyword names derive from the validator's bundled official meta-schemas; genuine subschemas are
enumerated using referencing.Resource, not a custom schema parser or a walk over arbitrary example data.
Only fragment references are admitted, resolved with the library's public APIs; no remote/file retrieval.
Authoring analysis follows both genuine subresources and resolved reference targets to a finite closure,
carrying each Resolved.resolver. A reference can promote const/example data into an executing schema; such
targets must also pass the authoring policy. Unreferenced literal data remains data. Analysis is bounded;
cyclic references cannot grow an unbounded worklist. The profile is static: $dynamicRef/$dynamicAnchor
and deprecated meta-schema keywords are explicitly refused. Independent review disproved a proposed
dynamic-scope deduplication key; implementing a second dynamic resolver/binding analysis is unnecessary
for local tool contracts. Static refs/anchors and their referenced-data closure remain supported. This
uses a complete mature validator within a declared local authoring profile, not unrestricted 2020-12.
This profile intentionally excludes custom vocabularies/annotations. format remains the standard annotation,
not an automatic date/URI assertion. JSON Schema integer includes 2.0; built-in integer consumers adapt
validated values explicitly. Do not silently redefine the standard's numeric type.

Description is at most 512 UTF-8 bytes; schemas and the entire published definition are bounded by
MAX_CONTEXT_BYTES. Built-in
declarations are data outside the control loop. UTF-8 byte budgets, ordinary workspace-path constraints
and business/resource checks remain separate preconditions, with their limits stated in descriptions.
Trusted schemas and preflight functions are developer code; imported asset data never registers code/schema.
This is not a sandbox or a guarantee against hostile validators/handlers.

### Execution, result and feedback

Validate strict JSON parameters against the captured schema before task admission. Inside _admitted,
check the existing sequence, effect, budget and unresolved operation rules, then run optional non-effecting
preflight. Only afterward persist the definition blob and invoked record. Run the actual handler outside
the transaction, as before. Record the captured definition ref with the invocation.

All results contain outputs, whose entries have ref/name/media_type and refer to real stored bytes.
Optional outputSchema is enforced after execution; malformed outputs or schema failures cannot earn ok.
Any post-execution write failure remains unknown regardless of whether the error is useful or expected.
The operation digest remains tool name plus parameters: replacing metadata does not bypass unresolved calls.
The synthetic host.model identity is reserved and shared by internal calls, operation keys and history
lookup; a separately registered model tool has a distinct operation namespace.

FairyError is an explicitly public protocol diagnostic, including optional public details. Its serialized
projection uses the event store's canonical encoding, has a fixed byte budget and validates all keys and
values, rejecting non-string keys, non-JSON values and control characters; invalid diagnostics
fall back to a safe constant. Handlers must not put secrets or raw material in public errors. Other exception
text is never forwarded. Schema validation emits a bounded list of rule/schema pointers only; unknown
instance-property names and rejected values are not copied. These rules apply before and after execution.

### Discovery and historical explanation

capabilities --query TEXT lists only name/effect/description/contract_ref; next includes at most its existing
eight summaries. capabilities --name NAME retrieves the complete current definition using inputSchema and
optional outputSchema. Full definitions are not injected into every work packet.

Invoked records link definition blobs. Ordinary inspect/receipts retain refs, without embedding schemas.
inspect TASK --contract REF retrieves one historical definition only if that ref belongs to the task's
recorded calls; closed tasks remain inspectable without a new counted invocation. This survives live
registration changes. The hash does not certify the handler's behavior.
Context content access includes its own recorded tool definitions. No new asset promotion or executable
sharing path is introduced. Full-history/context growth remains the separately open R02-D02 boundary.

### Dependency preparation and distribution

pyproject.project.dependencies is the pin authority for the complete selected runtime closure. An offline
development generator reads fixed official PyPI release JSON snapshots plus a digest manifest and produces
the portable requirements-runtime.lock and packaged diagnostic pin data. Check mode verifies identities,
active transitive requirements and exact generated consumers. No copied hand-maintained version list.

The host uses standard python -m venv in an approved directory and that interpreter's pip install
--require-hashes --only-binary=:all: -r requirements-runtime.lock once, then reuses the interpreter.
No global package install or custom installer/resolver. Unsupported wheel environments fail explicitly.
doctor and schema remain usable without runtime dependencies through lazy validator imports. Broken or
wrong dependency versions prevent ready/task creation. Optional wheel installation uses the same declared
pins; release verification prepares locked dependencies before --no-deps project installation.

Source skill/ZIP tests now run with dependencies prepared and assert local runtime selection. The old -S
stdlib-only promise is removed, not emulated. Fresh target-local venv, hash-lock rejection, portable launcher
and wheel execution are separately exercised. Existing bootstrap/docs/CI must reflect this changed contract.

## P4: Validation obligations

- Real differing integer/range and string/list/enum tools are distinguishable through supported discovery.
  Invalid/null/bool/extra/missing values stop before handlers/events/budget/blobs; corrected input succeeds.
- Schema source/returned-descriptor mutation cannot change enforcement; invalid schemas, misspelled
  keywords, unsupported dialects, unresolved/remote/file refs fail safely without I/O. Local refs, examples
  containing literal $ref/keyword strings, standard numeric semantics and annotations have positive controls.
- Real preflight checks obey sequence/permission/budget and do not convert known refusal to write unknown.
  Real post-write exceptions and output failures remain unknown and block duplicate retry after re-registration.
- Public corrective errors survive; unexpected/private/dynamic-key values never leak through generated
  diagnostics; oversized/control/non-JSON public errors fall back safely. Failed output metadata never publishes.
- Definition snapshot/receipt survives registration changes; default catalog/next/inspect never dump full
  schemas, explicit historical lookup is task-scoped, and repeated registrations do not embed schema copies.
- Missing/broken/wrong dependencies diagnose without home creation for both entrypoints; fixed-wheel
  install and hash tamper controls; fresh prepared venv source-copy/ZIP/wheel full task; no hidden install.
- Run canonical gates, F01/F02 composition controls, independent P4 and final record/source identities.

## P5: Completion

Only R06-D01 may become verified after bounded independent technical verification. Store/protocol format 3
cleanly replaces the previous format; no migration or compatibility branch. Preserve previous frozen
evidence and pending maintainer acceptance. Remaining findings, recovery/context candidates and real-user/
long-term outcomes are not closed by this batch. Results/termination belong in the F03 report and repair ledger.

P1–P3 independent clearance and P4 final verification are complete. P4 executed 22 core groups and 20
reference edge cases, plus fresh prepared source/ZIP/wheel task delivery and artifact identity checks.
The executor's 92 runtime and 12 development tests and five real installer layouts also passed; these
are separately attributed evidence, not claimed as a second independent full-suite run. R06-D01 alone
is technically verified. See the [F03 report](../repairs/F03-declared-tool-contracts.md) for scope,
remaining limits and the P5 termination declaration.
