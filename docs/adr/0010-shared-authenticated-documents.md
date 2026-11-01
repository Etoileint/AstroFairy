# ADR-0010: Shared authenticated documents and selected reads

Date: 2026-10-31. Status: implemented; P01 independently technically verified; maintainer/product acceptance separate.

## P1: Scope and assertions

F08 implements work-program P01, following the user's instruction to continue the original optimization
plan. P00's 15 scoped repair conclusions remain historical; they do not close P01–P07. Executor=root,
verifier=f08_independent_verifier, final arbiter=maintainer at every P1–P5 gate. FDP B independently
re-established the current costs, then this conceptual change proceeds through A. Only AstroFairy is
writable; no commit, publication, migration, compatibility reader or implicit data deletion.

1. Eliminate retaining every complete growing document prefix for append-history workloads. Share
   immutable values, scalar chunks and collection subtrees across snapshots, without expiring old refs.
2. A selected fragment must not read, hash, parse or serialize the complete document or selected large
   scalar. Authenticate every consumed block and navigation fact under the requested immutable root.
   Bound block payload size, fanout and per-call verified cache; do not replace hashes with file stats.
3. Preserve exact `_contracts.canonical` text: member order, array order, Unicode/escaping, numeric
   spellings and accepted integer domain. Huge values and keys remain chunkable beyond ordinary blobs.
4. Keep scope, task/seq, zero-budget/closed-task access, original execution facts, safe errors and the
   exact 24 KiB final CLI response cap. Do not confuse presentation identities with artifact references.
5. State the integrity contract change explicitly: selected reads establish selected authenticity;
   a separate full audit checks every reachable block. A successful selected read no longer claims
   to detect damage in an unread sibling. Whole-document audit remains available and independently tested.
6. No universal storage/latency bound: constructing a snapshot may traverse the full native value;
   early insertion can shift fixed collection block boundaries. Full event replay, lifecycle/retention,
   SQLite page overhead, real model/human outcomes and native-host integration stay separate work.

## P2: Mature mechanisms and authority

Official originals, URL/version/SHA256/read scopes and executable probes are retained under
`.evaluation/repairs/F08/primary/` and `independent/`. Full download is not full-page review.

- [IPLD content addressing](https://ipld.io/docs/motivation/benefits-of-content-addressing/) provides
  established block authentication and shared-block deduplication. This design uses that pattern,
  not an IPFS daemon, CAR transport, CID/multicodec stack or a claim of IPLD codec compliance.
- [Linux fs-verity](https://docs.kernel.org/filesystems/fsverity.html) authenticates accessed pages
  through a Merkle tree. It supports distinguishing requested-byte authenticity from unread-data health;
  the filesystem-specific implementation is not a portable dependency for this skill.
- [RFC 9162 §2.1](https://www.rfc-editor.org/rfc/rfc9162#section-2.1) distinguishes inclusion proofs and
  whole-tree work, and separates hash domains. Our typed/versioned canonical nodes form a Merkle DAG,
  not the Certificate Transparency tree/proof protocol.
- [SQLite table guidance](https://www.sqlite.org/withoutrowid.html) and
  [transactions](https://www.sqlite.org/lang_transaction.html) provide indexed durable block lookup and
  atomic graph publication. Use an ordinary rowid table with an indexed unique reference: official
  guidance favors rowid tables for larger BLOB rows. SQL rows locate bytes; hashes, not an index row,
  authenticate them.
- [SQLite JSONB](https://www.sqlite.org/json1.html#the_jsonb_format) still documents O(N) operations;
  a monolith would not solve sharing or authenticated selected I/O. Python's mature incremental BLOB
  API alone also does not authenticate a range or route an RFC 6901 selection.
- The existing pinned python-json-pointer remains the RFC 6901 parser/resolver over lazy
  Mapping/Sequence adapters. Do not implement another pointer parser or substitute SQL JSON paths.
- The official [filelock 4.2.6 release](https://pypi.org/pypi/filelock/4.2.6/json) provides the native
  cross-platform schema-admission lock. Its exact wheel/source supports `fallback_to_soft=False` and
  `preserve_lock_file=True`; no existence-based fallback or lock-path deletion is permitted.
  The proposed [os.link](https://docs.python.org/3.12/library/os.html#os.link) publication approach was
  rejected after [SQLite's alias/journal warning §2.5–2.6](https://www.sqlite.org/howtocorrupt.html):
  it adds a filesystem requirement and an unnecessary transient alias. It was not implemented.

Compared full IPLD/CAR codecs, verified byte streams and typed array storage: these cover parts of the
problem but not the combined existing JSON value domain, owner binding, pointer access and snapshot
sharing. For example, [DAG-JSON](https://ipld.io/specs/codecs/dag-json/spec/) reserves certain map forms
and has its own serialization rules. Adding a codec still requires a project layout
and selection adapter. Keep existing SQLite/hashlib/JSON/pointer mechanisms, add only the hash-locked
native filelock dependency, and implement the document representation; no new database engine,
cryptography or workflow service.

## P3: Representation and access

### Bounded typed blocks

Replace monolithic document files with a separate derived SQLite block archive in the approved home.
It is not the task-event authority or the ordinary 16 MiB blob table. A transaction publishes all new
blocks before returning a root. Unsupported archive metadata refuses before schema mutation; reads
never create a missing archive. Existing corrupt blocks must fail on reuse, not pass INSERT OR IGNORE.
Files retain private POSIX permissions. SQL errors stay safe and never silently recreate the archive.
All writers acquire the same private, stable initialization lock before exclusive file creation or
existing metadata validation. Use the pinned FileLock with a finite 10-second timeout, mode 0600,
`fallback_to_soft=False` and `preserve_lock_file=True`. Keep the lock object alive through schema
commit/validation, then release it before normal graph BEGIN IMMEDIATE. Native OS locking is required;
unsupported/import/backend failures refuse with safe diagnostics, not a soft-lock or retry workaround.
An existing empty or malformed archive is never initialized as fresh. Reader/audit paths never acquire
or create that lock. A committed root can only be known after schema initialization and graph commit;
an unpublished empty file is not a document handle. Crashed initialization may leave an explicitly
refused archive and must not trigger automatic reset. All live SQLite connections use the canonical
archive path; there is no temporary-image or hardlink alias. Connections close even if lock exit fails.

Each persisted block is a canonical JSON manifest of at most 16 KiB. SHA256 covers a fixed version/type
namespace and its complete manifest. Kind, child identities/order, counts, UTF-8 byte lengths and
Unicode character spans are committed. The root also commits the exact owner and logical value root.
No unverified row may map a trusted flat hash to an unrelated representation root.

The layout has only document, logical scalar/array/object, scalar-text chunks/concatenations, and
collection leaves/index groups. Use fixed fanout 16 and bounded scalar text chunks. Scalars are encoded
through the existing canonical function; their text chunks can split escape sequences because complete
concatenation retains the exact encoding. No SQL numeric coercion or alternate JSON canonicalization.
Member keys are chunked scalar strings, never unbounded names in a manifest. A bounded raw-key prefix
and raw-key length aid ordered lookup; full audit checks their consistency. A matched key is verified
against its actual string before returning its value.

Array/member leaves group at most 16 entries. Index groups commit child counts/spans and group at most
16 children, recursively. Arrays preserve order; members follow the existing Python canonical key order.
An append reuses completed prefix groups and rebuilds only the tail path; nested source values are shared.
Early insertion or key insertion may shift later grouping boundaries and rewrite metadata. Measure it;
do not claim universal logarithmic update cost. Changing every byte necessarily creates new data.

Build from the native JSON value using the existing normalization semantics. Traversal must not silently
reduce accepted nesting or key/integer domains. Construction may process the complete value; this is
not an incremental State/replay change. Reuse uses authenticated existing blocks, with comparisons on
hash collisions/corruption. No global mutable parse cache or unverified cross-read success cache.

### Indexed selection and range rendering

Expose logical objects/arrays as lazy Mapping/Sequence views. Use the pinned resolver; scalar views
remain nonindexable, including its duck-typing fallback. Reject append sentinels and all existing invalid
pointer cases with fixed diagnostics. Never materialize source data for an exception representation.

Lookup array entries through authenticated counts; lookup members through ordered index entries and
bounded key prefixes, reading a full key only when needed. A huge selected key can require work
proportional to that key, without reading unrelated large values. Verify matching key bytes and every
consumed node's expected kind, counts and span. Source seq is obtained through the same authenticated
value tree, rather than a second unauthenticated lookup record.

Render only the requested character range by skipping committed child spans and visiting relevant
chunks. Reconstruct canonical text exactly. The per-read cache contains only bounded already-verified
immutable node bytes; it expires with the read. Fetch at most one context-sized text candidate, then
apply the existing exact final-envelope byte calculation. No full selected-value hash in this path.

`document` now identifies the versioned owner-bound root; `selection` identifies its typed logical
subtree commitment. **Neither is SHA256 of the returned canonical text or an ordinary artifact ref.**
Keep document/selection/pointer/offset together across fragments. Concatenation recovers canonical text;
plain hashing that text does not reproduce the typed commitment. This is protocol/store format 6,
with no version-5 reader, alias, migration or fallback.

### Full document audit and corruption semantics

Add the free administrative command `audit-document DOCUMENT [--task TASK]`. It verifies all reachable
nodes/chunks, edge kind/count/span consistency, scalar canonical encoding, member ordering/key metadata,
and owner/root binding. It returns bounded counts and a separately named `canonical_sha256`, computed
by streaming the complete canonical logical value once. This ordinary digest is distinct from typed
`selection` and `document`; it supports comparing a full reconstruction with the audit result.

Selected reads guarantee only authenticated requested bytes/navigation. Corrupt selected blocks,
root metadata, owner or used navigation fail closed. Corrupt unread siblings may coexist with a valid
selected read and must be reported by full audit. This intentionally replaces format 5's whole-file
scan on every read; it is not the same discovery scope. No selected response may claim whole-document
health. Audit traverses the graph/content, with additional navigation work, and may materialize a complete large scalar;
it is not repeated automatically for every fragment.

### Composition and failures

The document archive is a storage adapter; it cannot append task events, invoke handlers or change
permissions/revisions. Presentation retains the response cap, controls and exit-status behavior.
Learning still captures source and creates the maintenance child in the existing event transaction;
its immutable root may share blocks with earlier captures. A child rollback can leave unreferenced
derived blocks. Projection failure after effects retains authoritative recovery identities and facts.
No automatic GC, retention schedule, event checkpoint or task-event replay optimization is included.

The work-program scope checker separately connects all original checks/requirements/scenarios/objects
and notes to continuing work. It cannot turn routing or 15 technical repairs into overall acceptance;
real members and long-term benefits remain explicit evidence obligations.

## P4: Required independent checks

- Canonical root/subtree reconstruction, primitive types, Unicode/control escapes, giant keys/scalars,
  numeric/nesting domains, deterministic roots and owner separation; existing pointer/error controls.
- Root/node/chunk substitution, missing/truncated/wrong-type blocks, incorrect stats/key prefixes,
  stale lookup data, corrupt existing-block reuse and full audit versus unselected sibling damage.
- Instrument bytes/nodes parsed/hashed for tiny sibling and late scalar fragments at increasing source
  sizes; prove no complete-source parse/selected hash, retain exact 24 KiB envelopes and safe errors.
- Retained block payload/node/file metrics at multiple append scales and unchanged freezes; include
  nonrepeating material, wide members, early insertion and metadata shifts. No elapsed-time-only claim.
- Large legal native results and learning snapshots, zero budget, closure/reopen/concurrent insert,
  rollback and real-effect projection failure, no source event changes or extra read invocations.
- Full gates, original historical identities, complete work-program routing, source/ZIP/actual wheel
  installation and final records. No real-user/native-host/indefinite scalability certification.

## P5: Closure

P1–P3, the native-lock design impact and P4 independently passed within P01. The first initialization
race and the overstatement of full-audit complexity were corrected and independently revalidated;
phase-specific source and failure evidence remains intact. Source, ZIP and installed wheel each passed
independent scripted CLI flows. The [F08 record](../repairs/F08-shared-authenticated-documents.md)
contains resource metrics, evidence identities, full limits and the six-field termination declaration.
Only P01 is technically verified. P02–P07 remain open under their own criteria; whole-program/product
acceptance remains with the maintainer. Final rebuilt containers are sealed against executed runtime
bytes, not described as reexecuted merely because their payloads match.
