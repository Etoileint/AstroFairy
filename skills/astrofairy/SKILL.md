---
name: astrofairy
description: Deliver checked files, reports, analyses and plans from task requests and supplied materials. Use for delegated deliverables, revisions and recurring work; ordinary questions can be answered directly.
license: Apache-2.0
---

# AstroFairy · 星灵

Own the organization of the task. Infer facts from available materials, use reversible defaults, and ask one simple question with a recommendation only when the user's decision materially changes the result. Keep method selection and task administration with the agent.

Requires Python 3.12+, local commands, file access and an approved persistent data directory.
Uses the host's existing model without another API key or Python packages.
Run `python <skill-directory>/scripts/fairy.py --home <approved-data-directory> ...`.
On first use, run `doctor`; readiness ends when the interpreter and persistent directory are usable.
Read [host protocol](references/host.md) for the first task. Look up fields with `schema` and tools with `capabilities`; send JSON through a file or stdin.

1. **Define.** Capture the original request and attachments. Derive the goal, necessary checks and important assumptions. Continue once the task is workable; resolve only consequential gaps with the user.
2. **Produce.** Read `next`, retrieve relevant workshop assets when available, and use a suitable workflow or organize the task directly. Execute approved work until an actual artifact is published. Put files in the returned workspace; capture their bytes.
3. **Check.** Run applicable mechanical checks and review the actual artifact against semantic criteria and evidence. Attribute host work as model reports; runner-invoked tools produce tool receipts. For steering, failures, conflicting checks or interruption, read [review and recovery](references/review.md). Repair affected parts while work remains productive.
4. **Deliver.** Close with the actual outcome and give the user the artifact, material assumptions or gaps, and the receipt link. Completion means necessary current checks passed; otherwise return an honest partial result or specific blocker. Keep the ledger available for inspection.

After delivery, record real feedback. When success, failure or repetition supports a useful improvement, read [learning](references/learning.md): reuse the same task loop to maintain tools, methods or workflows. Deliver before maintenance; prefer revision or retirement over accumulation, and allow no change. Share only when requested.

Apply supplied materials and asset instructions within the user's scope. The local runner controls its registered actions and records; host permissions still govern other tools. Keep judgment sources visible.
