# Changelog

All notable changes to this repository are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
