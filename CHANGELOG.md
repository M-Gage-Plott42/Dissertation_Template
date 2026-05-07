# Changelog

All notable changes to this repository are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A public license-scope notice clarifying that the tracked UTC Graduate
  Manuscript Standards PDF remains an official UTC document and is not
  relicensed by this repository.

### Changed

- Generalized AGENTS timeline guidance so the public template no longer refers
  to a private-project defense date.
- Expanded Markdown lint coverage to all public repository documentation
  surfaces.

### Repository

- Mark the GitHub repository as a template repository for the public reuse
  workflow.
- Require dependency review alongside template and Markdown checks in the
  protected default-branch ruleset.

## [1.1.2] - 2026-04-12

### Added

- A separate rendered exact-margin audit surface for the shipped template page
  families via `scripts/audit_dissertation_margin_exact.py` and
  `refs/editorial_audit/dissertation_margin_exact_policy.yml`, kept out of the
  default public-template CI contract.
- GitHub dependency review for pull requests and merge-queue checks via
  `.github/workflows/dependency-review.yml` and
  `.github/dependency-review-config.yml`.

### Changed

- README, AGENTS, CONTRIBUTING, and the standards index now distinguish the
  baseline template compliance stack from the separate opt-in exact-margin
  closeout lane.
- Existing GitHub Actions workflows now use workflow-level concurrency and
  `merge_group` triggers so required checks remain reusable in merge queues.

## [1.1.1] - 2026-04-11

### Changed

- Retuned the template title page to the UTC sample spacer family so the
  title-to-`By` gap and author-to-next-element gap match the rendered
  manuscript standards example more closely while preserving the 2-inch top
  title start.
- Hardened the rendered preliminary-pages audit to verify the title-page
  spacer family directly instead of relying on a looser manual-only visual
  interpretation.

## [1.1.0] - 2026-04-11

### Added

- A rendered-PDF UTC compliance baseline for the public template covering:
  hyperlink audit, font audit, preliminary-pages contract audit, abstract-cap
  audit, TOC sentinel audit, page-geometry sentinel audit, structural margin
  audit, and the generated margin proof overlay.
- `requirements-audits.txt` to pin the PDF audit parser/tooling surface used by
  the template validation stack.

### Changed

- Template CI now installs the pinned audit dependency set from
  `requirements-audits.txt` instead of floating to the latest `PyMuPDF`
  release.
- README, AGENTS, and CONTRIBUTING now describe the pinned audit dependency
  install step and treat the proof-overlay build as part of the current
  compliance baseline.

## [1.0.5] - 2026-02-17

### Added

- Repository governance files:
  - `.github/CODEOWNERS`
  - `CONTRIBUTING.md`
  - `SECURITY.md`
  - `CHANGELOG.md`

### Changed

- Default-branch naming/documentation alignment to `main` in README and AGENTS.
- Workflow hardening:
  - pinned GitHub Action SHAs for `checkout` and `markdownlint`,
  - explicit minimal `permissions` in workflows.
- Branch-protection ruleset updated to default-branch targeting with required
  checks (`template-checks`, `markdown-lint`) plus non-fast-forward/deletion
  protection.
