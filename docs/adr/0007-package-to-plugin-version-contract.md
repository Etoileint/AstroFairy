# ADR-0007: Package-to-plugin version contract

Date: 2026-10-31. Status: implemented and independently technically verified within F05;
maintainer acceptance pending.

## P1: Scope and invariants

F05 repairs R16-D02 in development metadata generation. Executor=root,
verifier=f05_independent_verifier, arbiter=maintainer at P1–P5. FDP C routes the changed
conversion contract through A. Existing authorization covers AstroFairy-only implementation,
development without compatibility branches, and bounded independent verification.

1. Keep the existing single literal `_version.__version__` source and setuptools dynamic attr consumer.
   Reading the version does not execute the module. This batch does not implement arbitrary Python
   declaration analysis or a new source language; the single-literal convention remains explicit.
2. Use the mature packaging.Version public parser for PEP 440 numeric/phase normalization. Never
   construct a target from the original numeric substrings. No extra runtime dependency or module.
3. The supported parsed domain is exactly three release components, epoch zero, optional a/b/rc
   prerelease, no post/dev/local segment. Refuse malformed/non-string values and unsupported semantics.
4. Every accepted source produces SemVer 2.0.0 syntax: ASCII integer fields without leading zeros,
   a→alpha, b→beta, rc→rc plus the parsed numeric counter. Equivalent accepted PEP 440 spellings yield
   identical output; order is preserved within the supported parsed domain.
5. Compute all rendered outputs before writing any consumer. Invalid/unsupported input makes no writes;
   check mode stays read-only and reports drift. The source literal is never silently rewritten.
6. Current manifests remain byte-identical for the current version. No version bump, release,
   compatibility path, new core rule or change to task/learning mechanisms.

## P2: Authorities and alternatives

Actual official snapshots, SHA256 identities and selected read scopes are retained separately in
`.evaluation/repairs/F05/primary/` and `independent/`. Current GitHub documentation snapshots are
observed current originals, not immutable upstream-version promises.

- [PyPA version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/):
  ASCII numeric domain, integer and prerelease normalization, ordering and distinct epoch/post/dev/local
  meanings. This is the maintained specification; PEP 440 is historical context.
- [packaging Version API](https://packaging.pypa.io/en/stable/version.html): release integers, normalized
  phase/counter, epoch and optional segment properties. The parser is already pinned as a development tool.
- [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html): clauses 2,9–11, numeric normal form, prerelease
  ASCII syntax and precedence. Syntax conversion does not certify public-API compatibility policy.
- [PyPA project metadata](https://packaging.python.org/en/latest/specifications/pyproject-toml/) and
  [setuptools dynamic metadata](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata):
  static and dynamic versions are both standard; attr with a literal is a documented ordinary source.

Compared alternatives: extending the old regex or manually stripping zeros still maintains a second
PEP 440 parser and can admit Unicode digits or erase unsupported fields. A SemVer parser alone cannot
normalize the source language; another target-parser dependency is unnecessary for this closed mapping
from integers and three fixed labels. Canonical-only source rejection is coherent but loses useful
standard normalization; use normalized-input acceptance instead. Standards-defined normalization is
the sole path, not an additional legacy path. A complete all-PEP-440 mapping would need explicit ordering
and identity semantics beyond this domain; no silent epoch/post/dev/local erasure or build-metadata encoding.

Moving the source to static project.version and generating the runtime literal was also compared.
Independent ordinary wheel builds demonstrated that changing the static source without generation
can produce new wheel METADATA with an old runtime literal. Preventing that new drift would require
a build hook/backend change or a new build-before-sync premise. Retain the mature dynamic literal
source rather than introduce that additional boundary for this repair. Source ambiguity beyond the
existing single-literal convention is not claimed solved by this batch.

## P3: Mechanism

Retain existing AST literal extraction, guard the resulting string type, parse once with Version,
then enforce the parsed profile. Render release components using their integer values; add the fixed
label and integer counter only for parsed prereleases. No source regex, target regex, coercion fallback
or additional version authority in production code. packaging remains development-only.

Accepted normalization includes leading zeros, canonical phase aliases/separators/case, implicit
prerelease zero, optional v/whitespace and explicit zero epoch as accepted by the maintained parser.
Nonzero epochs, short/long release tuples, post/dev/local forms, and invalid/Unicode-digit source
syntax refuse. No padding/truncation or local-to-build-metadata translation.

The domain's numerical release order and a<b<rc<final correspond to numeric SemVer releases and
alpha<beta<rc<final; prerelease counters remain numeric. Equal normalized source identities intentionally
share a target. The source text may be noncanonical; normalized wheel/package identity is compared
to the plugin target semantically, not by requiring raw source and target strings to be identical.

render finishes before sync writes, retaining the existing no-write-on-invalid and read-only-check
structure. Arbitrary later filesystem failures are not a new cross-file atomicity guarantee.
Host plugin loading, upgrades, discovery, publication rules and arbitrary source programs remain outside
this bounded conversion guarantee. The current 0.1.0a1 is not bumped or published.

## P4: Validation obligations

- Reproduce all release/prerelease leading-zero failures and Unicode digits through actual render/sync.
- Current/stable/alpha/beta/rc positive controls, zero and larger counters, normalized aliases and identity.
- Reject every unsupported segment, short/long releases, non-string, malformed and Unicode-digit values;
  both sync modes preserve existing bytes and path existence on failure.
- Valid check detects drift without writing; write converges and repeated write/check is idempotent.
- Independently validate target grammar with authoritative ASCII semantics, expected target strings,
  and same-domain pairwise PEP 440/SemVer order. Do not use the production converter as its own oracle.
- Real isolated builds for leading-zero examples demonstrate normalized wheel METADATA and expected
  plugin values; the current build and existing development gates still pass. No host certification claim.
- Freeze final source/consumer identities, preserve previous evidence, then independent P4 and P5 records.

## P5: Completion

Only R16-D02 may change to verified after independent technical validation. Results and the six-field
termination declaration belong in the F05 report/repair ledger. Both R02 boundary candidates, real-user
and host behavior, final maintainer acceptance and release authorization remain separate.

P1–P3 and final P4 have independent technical clearance: 28 accepted cases, 84 rejection/no-write
controls, 784 independent precedence/identity comparisons and three real wheel/sdist fixture builds.
The final non-string TypeError correction was independently frozen and rechecked; successful string
builds were not needlessly repeated. Executor evidence separately passed 102 runtime and 15 development
tests and the complete development gate. Only R16-D02 becomes technically verified; see the
[F05 report](../repairs/F05-package-to-plugin-version-contract.md) for evidence attribution and P5 closure.
