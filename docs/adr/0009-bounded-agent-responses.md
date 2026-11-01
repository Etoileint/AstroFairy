# ADR-0009: Bounded agent responses with lossless document access

Date: 2026-10-31. Status: implemented; independent P1–P4 technical verification passed,
including the P2 current-authority impact check. P5 is recorded in the
[F07 report](../repairs/F07-bounded-agent-responses.md). Maintainer acceptance remains separate.

## P1: Scope and invariants

F07 addresses R02-D02's whole work-packet consumption boundary. FDP B has re-established current
growth from source and executable probes; this conceptual repair proceeds through A P1–P5.
At every gate executor=root, verifier=f07_independent_verifier, final arbiter=maintainer.
Only AstroFairy is writable; no commit, push, publication, compatibility reader or migration.

1. Every successful or failed JSON protocol response emitted by the CLI must fit 24 KiB of UTF-8,
   including its final newline and any envelope/escaping. This is an explicit engineering policy,
   reusing the existing context budget, not a model-token or universal latency guarantee.
2. Legal native results, original events, current admission rules and evidence bindings remain exact.
   Native Python Workshop methods keep their full objects; the CLI presentation boundary is bounded.
   Do not turn a large valid result into a failed tool observation or a safe-repeat indication.
3. Oversized responses retain small control information and a lossless immutable document handle.
   Details are read without invoking a capability, consuming task budget or changing task revision.
   A handle identifies bytes and task scope; it is neither tool evidence nor authorization by itself.
4. Reads bind one immutable document and one selected JSON value. All JSON shapes, including one
   huge value/key and control-character escaping, have a bounded reconstructible fragment route.
   Invalid scope, missing/corrupt content, nonexistent selections and invalid offsets fail explicitly.
5. Learning captures a coherent source task/history snapshot and gives maintenance a small locator;
   no legal aggregate is forced through the 16 MiB ordinary content-blob ceiling.
6. A bounded response does not make replay, retained history or snapshot storage bounded. Those costs
   remain explicit. Unchanged documents deduplicate; this batch does not prune evidence or reset tasks.

## P2: Official precedents and alternatives

Official originals, SHA256 identities, selected read scopes and source-bound probes live under
`.evaluation/repairs/F07/primary/` and `independent/`. Downloads alone do not imply full-page reading.

- [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901): exact JSON selection, escape handling,
  canonical array indices and explicit resolution errors. Use the mature python-json-pointer library,
  pinned from official PyPI metadata, rather than a new pointer parser. Selection does not bound size.
- [Google AIP-158](https://google.aip.dev/158): continuations locate data and never replace resource
  authorization; collection growth requires a designed access boundary. This CLI exposes explicit
  character ranges of an immutable representation, not AIP opaque list-page tokens or an AIP API.
- [Kubernetes API concepts](https://kubernetes.io/docs/reference/using-api/api-concepts/#retrieving-large-results-sets-in-chunks):
  all continuation reads must refer to one coherent snapshot. No Kubernetes dependency is introduced.
- [MCP pagination](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/pagination):
  the official latest route resolves to 2026-07-28. Server-sized pages and explicit continuation/error
  remain relevant precedents. The latest version additionally specifies request metadata, cache/result
  fields and valid empty-string cursors; it is not identical to the initially read 2025-06-18 page.
  AstroFairy is an Agent Skills package, not an MCP server; explicit character ranges and null end do
  not claim MCP opaque list-cursor or full-protocol compliance.
- [Temporal Continue-As-New](https://docs.temporal.io/workflow-execution/continue-as-new):
  execution-history lifecycle is a separate mechanism; transport does not confer that platform's guarantees.

List-only cursors miss huge strings, parameters, schemas and nested results. LLM summaries and vector
retrieval may aid relevance but cannot replace exact requirements or contradictory evidence. Structural
lazy views add more projection contracts and still need a huge-value/key escape hatch. A hosted workflow
service adds lifecycle/infrastructure responsibilities without establishing a response byte invariant.
Choose a universal representation boundary plus standard selection and exact fragments.

## P3: Contracts and mechanism

### One presentation adapter

Add a presentation module beside the CLI, separate from task admission/replay. It may persist and read
derived documents in the approved home; it cannot append task events, invoke handlers or grant scope.
This adapter belongs with transport, outside the existing four-file control-loop growth budget. Do not
move existing control responsibilities out merely to evade that budget. Learning calls its snapshot
operation as composition; its source task and child creation stay in the existing transaction.

Keep a normal complete response inline when its canonical JSON plus newline fits. Otherwise persist
the complete value and return `deferred: true`, a document descriptor, and bounded control metadata:
task/seq/revision/action/status/call/outcome/budget/integrity where present, collection counts,
the first pending/conflicting call identity and selected artifact/candidate refs where available.
This is an explicit deferred response, not a truncated object or a semantic summary. The complete value
remains accessible. Exit status is computed from the original result, including nested mechanical checks.

All output paths, including errors and fragment replies, pass the exact serialized-byte check. Help and
argument-parser diagnostics are outside the JSON protocol. A presentation failure after execution
returns a bounded `projection_failed` error instructing inspection before retry and retaining the
authoritative runner task/seq/call and newly created learning/validation task ids when known, without
requiring a document write. In particular, a failed start response must still identify its committed
task so recovery is executable. Do not derive these identities from arbitrary nested tool result fields.
Already committed effects/observations remain recorded. A failed response export must never be treated
as a failed write.

### Immutable documents

Persist canonical UTF-8 JSON `{task: OWNER_OR_NULL, value: COMPLETE_VALUE}` under
`home/documents/SHA256.json` with the existing atomic-write/0600 operation. The hash covers both owner
and exact value. Validate the reference grammar before path construction; verify digest and owner on
every read. Documents form a separate derived representation, not ordinary task content blobs or new
tool observations. Task documents require the exact owner; global capability/asset documents use null.
Knowing a different task's hash does not allow a caller to claim it under the current task scope.
This remains a cooperative local-host boundary, not authentication against a hostile host with file access.

Reuse a matching existing document; corruption is an integrity error. Document reads remain possible
after task closure, registry changes and process restart. No expiry or implicit pruning is added.
Changed large snapshots require new full documents, so cumulative projection storage can grow faster
than raw history. This cost is explicit, not a retention/scalability claim; no snapshot is created for a
small inline response. Receipts and raw events remain their existing separate archival surfaces.

### Free selected fragments

Add `read DOCUMENT [--task TASK] [--pointer POINTER] [--offset N] [--limit N]` as a read-only CLI route.
POINTER is RFC 6901 string syntax, default empty, selecting the original value's root. No URI fragment,
Unicode normalization, default-on-missing or array append sentinel. The pinned upstream resolver performs
selection; resolver errors map to fixed safe diagnostics, never upstream exception text (which may
contain source data). JSON conversion rejects non-JSON sentinels. A raw-root fragment route covers keys that cannot
conveniently be supplied on a command line.

Return document descriptor, selected-value digest, character count, requested offset, exact text fragment
and `next_offset` or null. Text is the canonical JSON encoding of the selected value, so strings retain
their quotes/escapes. Concatenating all fragments reconstructs those exact bytes after UTF-8 encoding.
Offsets count Unicode code points in that canonical text. Requested limits are positive, capped at the
context budget; the server may return less. Measure the complete final JSON reply, reducing the fragment
to fit. A nonterminal read must make progress. Do not echo an arbitrarily large pointer/key into metadata.

Hosts retain document identity, selection digest and next_offset together. Current task changes create
new documents; old reads never silently switch snapshot. To use a new `next`, compare its revision/seq,
read necessary goal/criteria and every unprocessed forwarded answer before continuing, and inspect the
identified pending/conflicting attempt. Counts explicitly disclose deferred collections; a small work
packet does not assert that the host has consumed them. Reuse earlier immutable documents as context.

### Learning and development epoch

Capture full source inspection including raw events in the source transaction, freeze a document scoped
to that source task, and store only its small locator as the maintenance input blob. Its source task/seq
and document hash bind what is learned; free reads expose original answers, feedback, calls and checks.
Later source feedback produces a different snapshot; old maintenance inputs do not silently change.
Filesystem snapshots and SQLite are not one transaction: a rolled-back child can leave an unreferenced
derived file; a snapshot write failure rolls back child creation while leaving the source unchanged.

Use protocol/store format 5 without compatibility or migration. Add one pinned, hash-locked pure-Python
JSON Pointer dependency; all existing dependency pins remain unchanged. Doctor/setup still diagnose
missing dependencies without silently installing or importing them at CLI startup.

## P4: Independent validation obligations

- Exact final stdout cap, including newline/escaping, for ordinary and oversized next/start/inspect/history,
  invoke/check/close/deliver, capabilities, asset operations, learning and error responses; original exit codes.
- Current-use scenarios with many updates/criteria/pending calls/failures; first control info is actionable,
  goal/requirements/new updates and blocker details remain selectively reachable, and zero-budget continuation works.
- Full reconstruction for nested values, giant individual strings/keys, Unicode/control characters,
  one-character limits, RFC examples, invalid escapes/array indices/missing values and append sentinel refusal.
- Immutable pages across new events/restart; owner swaps, corrupt/missing files, path-like hashes and invalid
  offsets/limits refuse. No side effects, invocation charge, seq or revision change on free reads.
- Valid native results and learning source aggregates above 16 MiB; actual source snapshot and maintenance
  read/production/check/closure; old evidence/result/origin/review rules unchanged.
- Projection failure after real effects preserves committed observation and does not invite a duplicate write;
  source rollback behavior and reuse of identical documents; new snapshot disk/replay costs stated accurately.
- Complete gates, old-format refusal, unchanged historical review/repair records and actual source/ZIP/wheel
  distribution identity and use. No native-host, real-user quality or indefinite scalability certification.

## P5: Completion boundary

Only the selected agent-response consumption scope can close R02-D02 after independent technical P4.
Replay latency, full-history retention, cumulative snapshot storage, host token use and real-user outcomes
remain explicit engineering/acceptance limits. Results, residual obligations and termination belong in F07.
