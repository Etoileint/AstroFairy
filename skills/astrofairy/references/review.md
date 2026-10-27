# Checks and recovery

- `next` returns the current task revision, artifact, unresolved calls, criteria and issues.
- Tool success, model reports and quality judgments are different records. Check the artifact, not a paraphrase.
- Mechanical reviews can only be submitted by the runner's check path. A model cannot mark them passed.
- New artifact publication or a task revision invalidates prior reviews through version binding.
- A new pass does not silently erase a failure. For a semantic reassessment, list matching active event ids
  in `replaces`, provide the evidence and explain the correction in `basis`. A model cannot replace a tool review.
- Unresolved calls block complete delivery. Reopen the same home to recover the ledger. Fulfil a pending model
  request using its original call id; do not issue duplicate work. An interrupted tool call remains pending or
  unknown. Inspect its actual effects before deciding what to do; this version does not automatically reconcile it.
- Closed tasks reject new work but retain late reports, tool receipts and feedback. Follow-up work starts a new task.
- Invocation budgets count registered calls and model requests. They do not measure real model tokens or wall time;
  the host still controls those resources. Stop unproductive work before the hard count is exhausted.
- If completion is not attainable, deliver a useful partial result with specific gaps, or end as failed.

Database hashes detect altered records and blobs. They are local integrity checks, not protection against a host
that controls the database, code and hashes. Checkpoints and exports do not assert independent audit certification.
