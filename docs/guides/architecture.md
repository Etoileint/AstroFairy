# Architecture

AstroFairy organizes delegated work into usable delivery with inspectable evidence.
The user provides a task request and occasional consequential choices. The host owns semantic reasoning.

## Responsibilities

The control loop admits a proposed action, records its start, invokes a capability, and records observations.
`_kernel.py` owns admission and replay rules; `_store.py` owns durable content and events;
`_contracts.py` owns command parsing; `_runtime.py` composes the loop and host work packets.
These four files share a checked growth budget. Library and capability implementations are workshop assets
and adapters; they do not gain permission to change task scope or terminal state.

Task agreement, action proposal, execution result and review are separate protocol objects.
Model reports remain model reports. Mechanical reviews are produced through the actual checker path.
Requirements distinguish explicit user constraints, immutable runtime policy and derived assumptions.
Completion requires all necessary current checks to pass and no unresolved call or question.

## Persistence and revision

SQLite transactions serialize event updates with optimistic sequence checks. Original bytes are captured
in content-addressed blobs. The event chain is the task history; current state and reports are projections.
Task revisions and artifact publication bind reviews to the exact target. A pass cannot silently erase a failure.
Explicit reassessment retains predecessor ids, producer, rationale and evidence.

Starts are committed before effects. A process interrupted during a call leaves it unresolved, rather than
asserting failure or retrying. Closure stops scheduling while retaining late reports and observations.
Exports are reproducible projections; a failed export can be regenerated from the store.

## Workshop and learning

Methods, workflows, tools, cases, profiles and constraints grow outside the control protocol.
Lookup returns bounded metadata; relevant content is read on demand. A workflow gives instructions,
inputs, parameters and completion conditions to the host; it is not executable Python or a new core branch.
Repeated tasks, successful methods, failures, edits and feedback can drive maintenance.

Maintenance uses ordinary tasks. Adoption requires successful validation of the exact candidate package,
including an asset-fitness judgment. Changed bases reject stale adoption. Sharing transports an asset package,
never installs code, and requires local validation after import. Scope is a local namespace.
Retirement excludes an asset from active selection; immutable history supports inspection and new rollback proposals.

Behavioral constraints distinguish applicability, failure consequences, enforcement and explanatory purpose.
Facts, profiles and transient task state remain separate. Growth budgets are guardrails, not a proof
of permanent architectural completeness.

## Actual enforcement boundary

This is a cooperative host skill with a local runner, not a sandbox or independent hosted agent.
It enforces its own command protocol, registered operations, state transitions and review bindings.
It cannot prevent a host from bypassing the runner, lying about user input, editing its code/database,
or making unsupported semantic judgments. Hash chains are local tamper detection, not external attestation.
Filesystem guards protect ordinary path traversal; they are not race-proof isolation against a hostile host.
Invocation counts and content budgets are enforced locally; real model tokens and wall time remain host-managed.
Tool provenance means the runner invoked a registered handler, not that every handler is trustworthy.
These limits are part of the protocol's interpretation and must survive future integration changes.
