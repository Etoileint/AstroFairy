# Runtime preparation

The agent prepares the environment; users need not manage package versions or commands.
Use Python 3.12+ and a persistent directory approved for this task system. Reuse a prepared interpreter.
The runtime uses python-jsonschema for JSON Schema and python-json-pointer for RFC 6901 selection,
and filelock for native cross-platform archive initialization, with their hash-locked dependency closure.
The writer uses a stable private lock file, a finite timeout and no soft-lock fallback. Native locking
must work on the approved data filesystem; unsupported locking refuses safely. Reader/audit paths do
not acquire or create that lock. Delivery uses the same native-lock discipline on its own task directory.
Doctor checks imports/versions, SQLite capabilities and BagIt delivery readiness; actual archive locking is
exercised on its first writer, not certified by a read-only readiness result. Its search section keeps
dependency metadata, model-file presence and projection state separate: presence is never `verified`, and
default `doctor` neither opens/creates the task database nor hashes model bytes. `doctor --verify-search`
stream-hashes the six fixed model files without downloading, indexing or inference.
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

BagIt delivery uses the vendored `bagit==1.9.0` wheel in the skill's `scripts/wheels` directory. Prepare it
from the delivery lock once in the same prepared environment:

```sh
<approved-directory>/runtime/bin/python -m pip install --no-index \
  --find-links <skill-directory>/scripts/wheels --require-hashes \
  -r <skill-directory>/scripts/requirements-delivery.lock
```

The wheel is built from the official bagit 1.9.0 sdist with the fixed chain recorded in the development
vendor manifest. `doctor` reports `delivery.ready`; missing or mismatched BagIt blocks delivery exports,
while diagnosis and `schema` remain available. Do not build a replacement or install an unpinned bagit
during an ordinary task.

Local hybrid retrieval uses a separately locked search closure (LanceDB 0.41.0, FastEmbed 0.9.1,
ONNX Runtime, tokenizers and their dependencies). Prepare it from the search lock:

```sh
<approved-directory>/runtime/bin/python -m pip install --require-hashes \
  --only-binary=:all: -r <skill-directory>/scripts/requirements-search.lock
```

`assets prepare` explicitly prepares the fixed multilingual E5 ONNX model
(`intfloat/multilingual-e5-large`; source, revision and the six consumed file hashes are in the model
profile) and byte-verifies every declared file with SHA-256. It works with an empty active library, builds
no projection and runs no inference. `assets search --refresh` composes the same preparation service with
a projection rebuild. Set `ASTROFAIRY_MODEL_CACHE` to an approved persistent cache directory; otherwise
the per-home `search/models` directory is used. The model is about 2.2 GB and may take time on first
preparation; progress and failure are explicit, and competing preparations serialize on the shared cache.
Every explicit prepare/verify performs a new streamed verification; an earlier in-process success is not
reused after file mutation. Ordinary search does not download or start the model and returns
`search_not_ready` with the offending stage and recovery route. An explicit refresh on an empty active
library still prepares/verifies and returns `projection.state=empty`; a plain empty-library query does
not load the model. `doctor` reports the layered search observations while keeping core task readiness
separate.

For the optional Python package, prepare these same locked dependencies and install the wheel with
`pip install --no-deps <wheel>`. The standard skill folder remains the main installation unit.
The data directory stays separate from installed code and environment files.
