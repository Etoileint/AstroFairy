# Host protocol

The conversation host does the reasoning. The local runner manages state and evidence.
Use a single approved writable home. Keep returned task and call ids; users need not manage them.
Use `capabilities --query TEXT` to discover a bounded set of tools and their accepted parameters.
`next` is a read-only work packet and may be repeated without consuming invocation budget.
`schema` is generated from the parser's field table. `expected_seq` rejects stale submissions.

## First task

Run `start --request <original-request> --input <attachment>` (repeat `--input` for attachments).
An optional `--spec <file>` carries goal, criteria and assumptions. Each criterion has `id`,
`description`, `checker`, `parameters`, `origin`, `required`, and `basis`.
Use `origin: user` for explicit requirements; derived criteria remain revisable.
The runner's asset-validation criteria use `origin: policy` and cannot be weakened by a task strategy.
The defaults are provisional: relevant content (semantic) and nonempty bytes (mechanical).
Adapt criteria to the real deliverable. Available checkers are `semantic`, `nonempty`, `json`, `contains`.
`contains` takes `parameters: {"text": "required text"}`. More capabilities can be registered in Python.
Use `--read-only` when task operations must not write files. Internal records and delivery snapshots
still use the approved state directory. These effects do not authorize external host actions.

## Submit JSON

Run `submit <task> --file <json-file>` or provide JSON on stdin.

For conversation work:

```json
{"op":"request","purpose":"Produce the agreed deliverable","refs":[]}
```

The returned call id identifies the pending work. Submit the actual content:

```json
{"op":"report","call":"RETURNED_CALL_ID","text":"Actual deliverable","name":"result.md"}
```

This returns a content reference. Submit `{"op":"publish","ref":"CONTENT_REFERENCE"}`.
For real files created by host tools, put them in the `workspace` returned by `next`, then invoke
`file.capture` with a relative path. Raw bytes are retained without decoding.

Registered calls use `{"op":"invoke","capability":"NAME","parameters":{}}`.
Look up accepted parameters through `capabilities --query NAME`. Asset search returns metadata;
reading an adopted asset pins its exact version. Read large inputs with bounded `content.read` fragments.

Run `{"op":"check"}` for mechanical criteria, then semantic reviews:

```json
{"op":"review","criterion":"goal","verdict":"pass","basis":"Explain the concrete comparison with the goal","evidence":["CONTENT_REFERENCE"]}
```

Use `fail` or `unknown` when appropriate. Close with `{"op":"close","outcome":"complete"}`.
Other outcomes are `partial`, `failed`, `cancelled`. The runner writes the artifact and receipt under
its delivery directory. `deliver <task>` can regenerate that export. `inspect <task> --history` shows events.

## Human input

Use `ask` with `question`, `recommendation` and optional `options` only for a consequential choice.
Forward the user's actual answer or unsolicited steering with `answer` and `text`.
It changes the task revision. Reconcile the goal and recheck affected output.
`revise` takes `goal`, `criteria`, `reason` and optional `assumptions`.
Changing explicit criteria additionally needs `user_basis`, the event sequence of the new forwarded answer.
The runner validates that such an event exists; the host is responsible for forwarding it faithfully.
