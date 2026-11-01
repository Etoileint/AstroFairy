# Tool adapter contract

Read when implementing or adapting registered Python tools. Asset `tool-spec` documents remain passive;
importing an asset never imports a handler or registers a schema.

Use `Capability`, `Context`, `FairyError` and `Workshop` from `astrofairy`. A tool has effect, handler,
public description and input_schema; optional output_schema and non-effecting prepare serve distinct purposes.

```python
from typing import Any
from astrofairy import Capability, Context


def measure(context: Context, parameters: dict[str, Any]) -> dict[str, Any]:
    return {"outputs": [], "days": int(parameters["days"])}


tool = Capability(
    "read",
    measure,
    description="Measure one to three days",
    input_schema={
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 3}},
        "required": ["days"],
    },
)
workshop.register("domain.measure", tool)
```

Names use 1–128 ASCII letters/digits/underscore/hyphen/dot. Description is at most 512 UTF-8 bytes.
The internal model name `host.model` is reserved and cannot be registered as an adapter.
`capabilities --query TEXT` gives summaries; `capabilities --name NAME` gives the exact current definition.
Input/schema copies cannot change the registered contract. Register replacements explicitly with `replace=True`.
Whole definitions are limited to 24 KiB; schemas are resources read on demand, not background instructions.

The mature 2020-12 validator runs in an explicit local static authoring profile: object root, explicit
additionalProperties/unevaluatedProperties policy, no custom dialect/vocabulary, unknown or deprecated
keywords, dynamic references/anchors, or remote/file references. Static fragment refs and anchors are
supported, including referenced literal locations. Unreferenced examples/const remain data. Fragment
encoding/escaping is checked before library resolution. Numeric-like pointer tokens must be canonical
ASCII nonnegative integers; this conservative authoring restriction also excludes object members named
with noncanonical integer spellings. It avoids the resolver's Python-style array indices. Standard
integer includes 2.0; convert validated integers for Python APIs where needed. format is an annotation;
use a separate declared business precondition for dates or other semantic requirements.

Input validation precedes invocation records and budget charges. A prepare callback runs after the
task's sequence, permission and budget checks but before invoked. It must not mutate parameters or
perform effects; it can check distinct resource/UTF-8-byte/business conditions and raise a public refusal.
It is trusted adapter code, not a sandbox. The actual handler runs outside the database transaction.

Return a JSON object with outputs. Each output has a known SHA256 ref, single usable name and nonblank
media_type; name is at most 200 UTF-8 bytes. Store actual output bytes through context.store.put first.
Other result fields may carry task data. Optional output_schema further validates the actual result.
Failed output validation never earns ok; write errors after invocation remain unknown and cannot be
blindly retried, even after changing the registration.

FairyError(code, message, details=...) is an explicitly public diagnostic. Give a safe actionable reason;
never put secrets or raw materials in it. Codes/messages must be usable and free of controls, and the
serialized diagnostic must fit 4 KiB. Invalid diagnostics fall back safely. Generated schema errors expose
only bounded public schema pointers/rules, without rejected values or dynamic instance-key paths.
Unexpected exception text is not forwarded.

Invocations store immutable definition refs. Inspect a past definition with
`inspect TASK --contract REF`; it must belong to that task's recorded calls and remains readable after
closure/re-registration. Ordinary next/inspect/receipts contain references, not embedded schemas.
Definition hashes identify declarations; they do not attest to handler code or semantic quality.

## Optional authoritative reconciliation

A write capability may set `reconciler="domain.verify"`. The runner requires a registered read capability
accepting exactly `{call: ORIGINAL_ID}`, captures its definition blob and pins its name/hash before the
write. Both definitions are task-owned historical references, readable after later registry changes.
Once a task has pinned that reconciler name, using that name requires the exact target input and matching
frozen authority; extra/missing input cannot downgrade it to an ordinary read.

`Context.call_id` is the durable invocation id, available before the handler executes; preflight and
non-invocation contexts have None. Arrange any provider token/atomic receipt needed to correlate that
attempt. This field is not a business-idempotency or external at-most-once guarantee. Do not infer
attempt completion from a parameter hash, matching file contents or a resource that happens to exist.

Return the ordinary outputs plus this object only on authoritative final confirmation:

```json
{
  "outputs": [],
  "reconciliation": {
    "target": {"call": "ORIGINAL_ID", "operation": "ORIGINAL_OPERATION", "contract_ref": "WRITER_REF"},
    "final": true,
    "result": {"outputs": []},
    "basis": "Identify the authoritative completed attempt receipt"
  }
}
```

The full reconstructed result must satisfy the writer's original outputSchema and common result rules;
capture its blobs and include each exact descriptor in the verifier's outputs with sufficient multiplicity.
Extra evidence outputs are allowed. Without a final answer, return no reconciliation object or `final: false`.
The native read still has its own contract and ordinary execution budget.

Comparison is exact canonical JSON, including ordered descriptors and all result fields. Adapters opting
in must provide reproducible results; merely compatible or reordered/transient data may cause a conservative
conflict. The derived `result_digest` identifies recorded data and is not a new blob reference or aggregate
16MiB limit. Ordinary tool results retain their previous storage boundary.

The original writer result/status is not overwritten. Current confirmation and sticky conflicts derive
from marked invocations and validated observations, with no extra acceptance event. See
[recovery interpretation](review.md) for late observations, closed receipts and honest fallback.
