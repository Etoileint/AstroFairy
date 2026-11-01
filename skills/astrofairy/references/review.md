# Checks and recovery

- `next` returns the current task revision, artifact, unresolved calls, criteria and issues.
- Tool success, model reports and quality judgments are different records. Check the artifact, not a paraphrase.
- Mechanical reviews can only be submitted by the runner's check path. A model cannot mark them passed.
- Reviews bind to agreement revision and immutable content. A different target needs its own checks;
  same-content republication and canonical no-op agreement edits preserve existing judgments.
- A new pass does not silently erase a failure. For a semantic reassessment, list matching active event ids
  in `replaces`, provide the evidence and explain the correction in `basis`. A model cannot replace a tool review.
- Unresolved calls block complete delivery. Reopen the same home to recover the ledger. Fulfil a pending model
  request using its original call id; do not issue duplicate work. An interrupted tool call remains pending or
  unknown. Inspect the original attempt and its pinned reconciliation declaration before choosing a next step.
- Closed tasks reject new work but retain late reports, tool receipts and feedback. Follow-up work starts a new task.
- Invocation budgets count registered calls and model requests. They do not measure real model tokens or wall time;
  the host still controls those resources. Stop unproductive work before the hard count is exhausted.
  At zero budget, existing results can still be reported/published, answers forwarded and semantic reviews
  recorded. Follow next's current issues; required mechanical checks are not exempted.
- If completion is not attainable, deliver a useful partial result with specific gaps, or end as failed.

## Authoritative attempt confirmation

For a writer that explicitly declares a reconciler, inspect that pinned definition with
`inspect TASK --contract REF`, then invoke the declared read tool with exactly `{call: ORIGINAL_ID}`.
Its real final observation must bind the original attempt/operation/writer contract, satisfy the frozen
writer result schema, and capture the outputs. The runner derives confirmation from those recorded facts;
the original unknown/pending status and original result remain visible. A model or human success claim
cannot substitute for this tool evidence. No new verdict command is needed.

This is a strict reproducible-full-result profile: descriptor order, multiplicity, names, media types,
numbers and other fields matter. Nonfinal replies, absence, failures or insufficient authority leave the
attempt unresolved. Mere file existence is not proof of which attempt created it. Read verification still
needs its normal permission/budget; without them use an honest partial/failed/cancelled result.

Confirmation concerns the old attempt even if the user has changed the task. Check the current artifact
against current requirements separately. Confirmation does not authorize retry, rerun deferred handler
actions, or grant an external exactly-once guarantee.

`execution_settled` and `execution_conflicts` report current execution integrity. Any contradictory positive
writer/verifier result stays disputed; later matching or unknown results do not erase it. `inspect_conflict`
means stop asserting complete and inspect the evidence. This release has no force-clear action.
Closed tasks stay closed; their recorded outcome is historical. New receipts disclose current dispute,
and future adoption cannot use a conflicted validation. Existing sent files/adopted assets are not globally revoked.

Late facts commit before receipt refresh. Export failure preserves the ledger; `deliver` regenerates the
projection. A receipt's `seq` identifies its snapshot and can lag the ledger. Read `next`/`inspect` for current
facts, and check integrity fields as well as the historical outcome. Never advertise a disputed complete
as an unqualified current success.

Database hashes detect altered records and blobs. They are local integrity checks, not protection against a host
that controls the database, code and hashes. Checkpoints and exports do not assert independent audit certification.
