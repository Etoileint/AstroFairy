# ADR-0006: Consistent Unicode discovery and SQLite admission

Date: 2026-10-30. Status: implemented and independently technically verified within F04;
maintainer acceptance pending.

Technical record closure: 2026-10-31 UTC.

## P1: Scope and invariants

F04 repairs R07-D01 and R12-D01. Executor=root, verifier=f04_independent_verifier,
arbiter=maintainer at P1–P5. FDP C routes these behavioral changes through A. Authorization covers
implementation inside AstroFairy, without development compatibility, sibling edits or publication.

1. Query terms and searchable metadata use exactly Python str.casefold for caseless literal matching.
   Copying a Unicode metadata term must not lose it merely because SQLite lower handles only ASCII.
2. Discovery remains metadata-only: name, summary and tags, at most 16 whitespace-separated query
   terms, OR matching and term-count score (repeated terms retain their repeated weight). Empty queries
   list eligible heads. Limits remain 1–10; the public tool schema shares that limit authority.
   Tags contribute their string values, not JSON punctuation
   or serialization escape sequences.
3. Only the latest adopted active head per scope/name is scored. Candidates and retired versions
   remain excluded, scope filtering is retained, and a nonmatching head cannot expose an older version.
4. Readiness and actual store admission share one real SQLite capability probe. Unsupported engines
   refuse before home creation, chmod or persistent database access; readiness creates no persistent data.
   The required SQL features include window functions and materialized common-table expressions.
5. Actual database connections and the probe share SQL-function/configuration setup. Failure closes
   every opened connection and returns safe corrective guidance, without raw exception text.
6. No new persistent index, duplicated normalized data, lifecycle state or core module. Existing format 3
   stays valid because storage representation is unchanged, not through a legacy compatibility path.

## P2: Authorities and alternatives

Official originals, SHA256 identities and actual selected reading scopes are retained under
`.evaluation/repairs/F04/primary/` and the independent evidence directory.

- [Python 3.12 str.casefold](https://docs.python.org/3.12/library/stdtypes.html#str.casefold):
  standard Unicode default caseless transform, including sharp-s expansion.
- [SQLite lower](https://www.sqlite.org/lang_corefunc.html#lower): built-in lower handles ASCII only;
  using it against Python-casefolded queries does not share a comparison relation.
- [Python SQLite create_function](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.create_function):
  public connection-local callable registration and deterministic-function support.
- [SQLite window functions](https://www.sqlite.org/windowfunctions.html#history): window support is a
  distinct engine capability; the Python version alone does not establish it.
- [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html#fk_enable): enforcement is enabled and
  verified per connection; merely accepting the enabling PRAGMA does not prove the feature is present.
- [SQLite materialization hints](https://www.sqlite.org/lang_with.html#materialization_hints):
  AS MATERIALIZED forms an optimization fence using an ephemeral memory/temp table; this is a distinct
  engine prerequisite, available since 3.35.0. The selected engine is checked by execution, not that number.
- [SQLite FTS5](https://www.sqlite.org/fts5.html#tokenizers): unicode61 tokenizes according to Unicode 6.1
  and removes Latin diacritics by default; trigram has different substring and short-query semantics.

Compared alternatives: ICU supplies mature Unicode processing but adds extension provisioning and a
different versioned case relation. FTS5 would introduce tokenizer/index maintenance and change matching
semantics; neither its default tokenizer nor a trigram index is a transparent repair for short literal
queries. Persisted folded columns duplicate data and require index/version lifecycle decisions. A Python
full-library scan moves ranking/filtering/limits out of SQL without a demonstrated benefit. Embedding or
hybrid retrieval answers a different semantic-recall requirement and needs its own measured justification.
The standard SQLite callable bridge to Python's existing casefold provides the required relation directly.

Removing the window query via a more complicated correlated query would obscure head selection without
evidence of a necessary platform benefit. A real capability probe is stronger than accepting a version
string and handles a feature-disabled build. No custom SQLite loader or alternate engine is introduced.

An initial implementation repeated the metadata callback for each term. A measured P3 return compared
three designs on the same 2000 directly seeded synthetic heads, N=3 per query shape: the initial 16-term
scan took 0.61–0.63 s; materializing selected head metadata took 0.045–0.052 s; a single four-argument
score callback took 0.11–0.14 s and was evaluated twice per head by this planner. That candidate used
strict JSON decoding of prepared query terms; it does not represent every possible raw-query score
callback implementation or prove a universal lower bound. The score callback is
a reasonable alternative without the newer CTE capability, but adds per-row query decoding and repeats
folding for filter/sort. Select materialization for this explicit measured duplicate-work case. It keeps
term scoring in SQL and introduces no persistent index/cache or new Python mechanism. Its ephemeral
metadata has memory/temp-storage cost; neither universal latency improvement nor a one-call guarantee
across every future query plan is inferred. Empty browsing does not normalize metadata.

## P3: Mechanism and limits

Register astrofairy_search_text(name, summary, tags) with deterministic=True on every connection through
one private connection factory. Its adapter decodes the stored tags using the existing standard JSON
parser, joins the actual metadata string values, and applies str.casefold. That factory also enables the
existing foreign-key policy. Library.search uses this callable and str.casefold for query terms. Select
current heads and scope before a prepared AS MATERIALIZED projection containing only returned fields
and folded metadata. Score that projection using parameterized terms, retain limits, and sort ties by
name then scope. For empty queries the projection uses a constant instead of calling the adapter.

SQLite readiness opens only :memory: through the same factory, executes a real AS MATERIALIZED CTE,
ROW_NUMBER window and Unicode callback positive control, verifies foreign-key enforcement, then closes.
Both doctor and Store construction consume this one check. Store construction runs it before any home
or database mutation. Setup/probe SQLite errors project to runtime_setup_required with fixed guidance
to use a Python/SQLite build providing the required features; version information is observation only.
doctor keeps dependency readiness separate and includes the SQLite result in overall readiness.

The matching contract is Unicode default caseless literal matching, not normalization-equivalent,
accent-insensitive, locale-tailored, transliterated or semantic search. No NFC/NFD/NFKC preprocessing
is silently added. Casefold may expand text (for example sharp-s) and follows the executing Python's
Unicode data. No normalized values are persisted, so an interpreter change cannot leave a stale index.
Scoring still scans eligible heads for query terms. Total cost also depends on stored versions/events,
metadata size and sorting; deterministic callbacks can be evaluated more than once per head. No index
or general performance improvement is claimed. Full-history/context growth remains R02-D02.

The memory probe checks required SQL capabilities/configuration, not disk permissions, durability,
all SQLite behavior, arbitrary corrupted stores or future platform compatibility. Native SQLite errors
on actual storage continue through the existing safe CLI boundary. Existing old-format refusal remains.

## P4: Validation obligations

- Reproduce the original Unicode miss through real proposal/validation/adoption and search entrypoints.
- Sharp-s, accented capitals, Greek sigma, CJK, ASCII, tags, literal punctuation and short-substring
  controls; explicitly retain negative normalization/accent/locale/semantic cases.
- Candidate exclusion, current-head-before-score, retirement, scope, OR scoring, 16-term cap, bounded
  results, empty query, deterministic ties, immutable content and reopening the same format.
- Unsupported window/callback/foreign-key capabilities and broken SQLite setup diagnose safely in
  doctor and reject Store before any new or existing home mutation; connections always close.
- Missing materialized-CTE support also refuses safely. Count callback evaluations for the chosen fixture
  and verify head/scope filtering, empty-query bypass and bounded results after this P3 optimization.
- Real current-engine positive and both module/launcher readiness paths; simulated missing features
  must be described as fault injection, not claimed as an actual old linked-engine execution.
- Canonical gates, prior repair composition and actual copied-skill/ZIP/wheel execution, source identity
  and independent verification. Only these two findings may change disposition after P4.

## P5: Completion

Results and the six-field termination declaration belong in the F04 report and repair ledger. Preserve
all frozen reviews and completed F01–F03 evidence. Maintainer acceptance, R16-D02 and both boundary
candidates remain separate; no commit, push, release or overall product acceptance is implied.

P1–P3, the measured materialization return and final affected P4 have independent technical clearance.
Final independent execution passed 156 general checks, 13 materialization checks, six supplemental
groups and source/ZIP/installed-wheel tasks, with 45 archive members bound to final sources. Executor
evidence separately passed 102 runtime and 12 development tests and its own three distribution tasks.
Only R07-D01 and R12-D01 become technically verified. See the [F04 report](../repairs/F04-unicode-discovery-and-sqlite-admission.md)
for evidence attribution, observed platform, limits and the six-field termination declaration.
