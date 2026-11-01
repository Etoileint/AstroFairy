# Release workflow

AstroFairy releases use Git tags and GitHub Releases in the public
[AstroFairy repository](https://github.com/Etoileint/AstroFairy). The standard skill folder is the
primary distribution; a portable ZIP and optional Python wheel/sdist accompany it. Publishing here
does not publish to PyPI or list a plugin in a marketplace.

## Prepare

1. Read the current repository instructions and obtain maintainer authorization to publish.
2. Check the remote branch, existing tags and releases. Never replace an existing released version.
3. Set the literal version in `skills/astrofairy/scripts/astrofairy/_version.py` and run
   `python dev/sync_metadata.py`. Use `v` plus the Python version as the Git tag, for example
   `v0.1.0a1`; plugin SemVer is generated under the [version contract](../adr/0007-package-to-plugin-version-contract.md).
4. Update both READMEs and add release notes under `docs/releases/`. Describe observed support,
   requirements, limitations and material changes. Alpha/beta/rc versions are GitHub prereleases.
5. Preserve frozen reviews, source manifests and original evaluation records. Append corrections
   and release decisions separately. Permission to release an alpha does not certify every
   long-term validation objective.
6. Run `python dev/check.py`. If a GitHub workflow changes, validate it with
   [actionlint](https://github.com/rhysd/actionlint) as well; Python tests do not validate workflow YAML.
   Inspect the exact candidate diff and file list for unintended files,
   private data and credentials. Commit through the configured hooks; never bypass them.

## Build and publish

1. Freeze the source in a commit. Build in a fresh directory populated by `git archive` of that
   exact commit, using the prepared build interpreter:

   ```sh
   python -m build --no-isolation
   python dev/package_skill.py
   ```

2. Verify wheel/sdist metadata and license; compare every distributed runtime/skill file with the
   committed source. Install the wheel in a fresh virtual environment using the hash-locked
   runtime dependencies; run the isolated wheel and extracted portable skill outside the checkout.
   Check `doctor` without creating state, then create a task. Verify the pinned installer URL and
   copied payload against this commit. Never reuse a pre-existing `dist/` as proof of current code.
3. Publish `SHA256SUMS` for the wheel, sdist and skill ZIP. Record the full source commit in the
   GitHub release body. Hashes identify bytes; they are not external signatures or attestations.
4. Push the commit, require that its GitHub `Check` workflow succeeds, then create an annotated tag
   on that commit and push the tag. Use a draft GitHub Release to stage the attachments and notes;
   verify their identities before making it a public prerelease. Do not mark it as the latest
   stable release. Never force-push or overwrite a published tag/asset.
5. Download the published assets into a separate directory, verify their checksums and confirm
   the tag points to the recorded commit. Keep local execution logs in the ignored `.evaluation/`
   directory; keep the public release notes useful without those local logs.

## After release

Collect real-user tasks and feedback with appropriate permission. Record the application, version,
task constraints, actual artifacts, receipt, resource accounting and observed limitations. Use these
to prioritize follow-up work; do not infer general quality or economics from a few examples.
Development stores have no backward-compatibility promise: retain old data and backups separately,
and use an approved fresh home when the store format changes. Fix release defects in a new version.
