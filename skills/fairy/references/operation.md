# Operation and recovery

All commands use the prepared interpreter and an explicit or approved home:

```sh
python <skill-directory>/scripts/fairy.py --home <home> doctor
python <skill-directory>/scripts/fairy.py --home <home> audit-state
python <skill-directory>/scripts/fairy.py --home <home> backup --out <new-directory>
python <skill-directory>/scripts/fairy.py verify-backup <backup-directory>
python <skill-directory>/scripts/fairy.py restore <backup-directory> --out <new-home>
```

`doctor` is read-only and does not create the home; its search observations separate dependency
metadata, model-file presence and projection (not checked). `doctor --verify-search` stream-hashes the six
fixed model files without downloading or inference. `backup` copies the main database first and the
document archive second, records file identities in `manifest.json`, and excludes workspaces, exported
deliveries, uncaptured environment state and external services. `verify-backup` rechecks identities and
the retained event/blob/document graph. `restore` requires a verified backup and a fresh destination;
it writes a `restore.pending` marker, copies bytes with SHA256/EOF verification, removes the search
projection and derived index, and removes the marker only after the restored state audits cleanly.
Interrupted restore or backup keeps the partial directory and blocks normal use of an incomplete home.

Retained snapshots and stable assets are restored; exported deliveries can be regenerated from captured
members. Unknown writes, uncaptured workspace files and external service state are not claimed as
recovered. A restored closed task reports action `deliver` because exported deliveries are excluded. Search
becomes `search_not_ready` after restore; prepare the model with `assets prepare` if it is absent, and
rebuild the projection with `assets search --refresh`. An invalid derived export may be replaced with
`deliver --repair --expected-seq S`; the old directory is quarantined and never deleted.

The fuller project maintenance explanation is outside the self-contained skill package. These commands
and the local receipt/BagIt recovery rules are the operational surface that ships with fairy.
