# Runtime preparation

The agent prepares the environment; users need not manage package versions or commands.
Use Python 3.12+ and a persistent directory approved for this task system. Reuse a prepared interpreter.
The runtime uses python-jsonschema for JSON Schema and python-json-pointer for RFC 6901 selection,
and filelock for native cross-platform archive initialization, with their hash-locked dependency closure.
The writer uses a stable private lock file, a finite timeout and no soft-lock fallback. Native locking
must work on the approved data filesystem; unsupported locking refuses safely. Reader/audit paths do
not acquire or create that lock. Doctor checks imports/versions and SQLite capabilities; actual archive
locking is exercised on its first writer, not certified by a read-only readiness result.
`doctor` and `schema` can run without them; a missing/broken/wrong dependency set prevents readiness and
task creation. No command silently downloads or installs code.

Python's linked SQLite must provide window functions, materialized CTEs, deterministic callbacks and foreign-key
enforcement. `doctor` executes a small in-memory probe through the same connection setup used by the
store; unsupported capabilities also refuse store creation before touching its home or database.
Python version alone does not establish these SQLite features. If the probe fails, choose a prepared
Python/SQLite build that provides them; changing packages in the virtual environment does not normally
replace the interpreter's linked engine. This probe does not certify disk durability or existing data.

For a fresh local environment, use standard venv and pip. Substitute actual approved paths:

```sh
python -m venv <approved-directory>/runtime
<approved-directory>/runtime/bin/python -m pip install --require-hashes --only-binary=:all: -r <skill-directory>/scripts/requirements-runtime.lock
<approved-directory>/runtime/bin/python <skill-directory>/scripts/fairy.py --home <approved-directory>/data doctor
```

On Windows the environment interpreter is `runtime\Scripts\python.exe`. Use the same prepared interpreter
for later launcher commands. Virtual environments are created on the target machine, not copied from another.
Dependencies may instead already be provided by the host, with versions matching the bundled pins.

The lock includes all selected runtime dependencies and allowed upstream wheel hashes. A missing compatible
wheel or hash mismatch is a preparation failure; do not disable hashes, build an unpinned replacement,
install globally, or repeatedly attempt installation during ordinary tasks. Use an already provisioned
wheelhouse with pip `--no-index --find-links <directory>` when working offline.

For the optional Python package, prepare these same locked dependencies and install the wheel with
`pip install --no-deps <wheel>`. The standard skill folder remains the main installation unit.
The data directory stays separate from installed code and environment files.
