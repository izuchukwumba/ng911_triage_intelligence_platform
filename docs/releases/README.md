# Releases

Each release has notes here (`<version>.md`) and an entry in the
[changelog](../../CHANGELOG.md). Design v1.2, section 14.3, requires every
release to include:
- a changelog;
- schema compatibility notes;
- rule and parser versions;
- test results;
- known limitations;
- reproducible demo instructions.

It also requires each release to be tagged, with the Git SHA recorded in its
evaluation reports.

| Version | Date | Notes |
|---|---|---|
| 0.1.0 | 2026-11-10 | [0.1.0.md](0.1.0.md) |

## How to release

1. On a release branch:
   - set the version in `backend/pyproject.toml`, `backend/src/ntip/__init__.py` and `apps/dashboard/package.json`;
   - move the `Unreleased` changelog entries under the new version;
   - write `docs/releases/<version>.md`.

   `tests/test_release.py` checks that these agree.
2. Merge the release PR once CI is green.
3. Tag the merge commit on `main` and push the tag:

   ```sh
   git tag -a v<version> -m "NTIP <version>"
   git push origin v<version>
   ```

4. The `Release` workflow checks that the tag matches the package version and re-runs:
   - the tests (against PostgreSQL);
   - the evaluation on the dev and regression splits;
   - the safety gate.

   It then publishes a GitHub release with the notes, and attaches the test and evaluation reports, which record the tagged commit's SHA. If any step fails, nothing is published.

Never re-tag a published version; fix forward with a patch release.
