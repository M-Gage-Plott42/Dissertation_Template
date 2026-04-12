# Changelog

All notable changes to this repository are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
