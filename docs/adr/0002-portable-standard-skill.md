# ADR-0002: Self-contained standard skill, shared distribution sources

Status: Accepted for layout and shared sources; the dependency-free runtime and `-I -S` execution
decision below are superseded by [ADR-0005](0005-declared-tool-contracts.md). Historical rationale is retained.

## Problem

A valid SKILL.md alone does not make installation portable. The first layout kept the Python runtime
outside the skill directory; a source installer copied instructions whose launcher could not import it.
A custom ZIP that repaired the layout hid this defect and created a separate distribution contract.

## Decision

The canonical deliverable is `skills/astrofairy/`, conforming to the Agent Skills specification.
Its scripts directory owns the runtime and its tests. The launcher resolves only its own directory.
It runs on Python 3.12+ without pip installation or third-party packages. Persistent user data lives
outside the installed skill directory, at the host's approved location.

The ordinary skills CLI or a directory copy can install that same directory. ZIP packaging filters
development files without adding a private manifest, injecting dependencies or relocating code.
The optional Python wheel builds the very same runtime source. There is no second implementation.

Native plugin metadata belongs in `.claude-plugin/`, outside the shared skill's frontmatter.
Version and author come from package metadata; the bundled license comes from the root license.
`dev/sync_metadata.py --check` rejects drift. `agents/openai.yaml` is optional host UI metadata.
No vendor-only invocation syntax, tool names or hooks are required by the shared entry.

## Validation and limits

Reference-format validation, isolated directory/ZIP execution and metadata drift checks run in the
ordinary check entry. Isolation uses Python `-I -S`, so a developer's editable install cannot mask a
missing runtime. An optional integration entry exercises the genuine skills installer in five
separate project fixtures, followed by isolated protocol delivery and receipt inspection.

Installer layout tests do not prove native application discovery, managed updates, model compliance
or semantic quality. These are recorded as separate limits rather than inferred from format validity.
No public repository or marketplace listing is invented; publishing remains a separate action.

## Basis

The [Agent Skills specification](https://agentskills.io/specification) defines the shared directory
contract. Matt Pocock's current distribution uses one skill source plus native plugin manifests;
its historical Codex limitation was superseded in the same ADR. The
[comparison report](../reports/mattpocock-alignment.md) records pinned sources and intentional differences.
