# Contributing

Thanks for improving the UTC Dissertation Template.

## Scope

- Keep changes aligned to UTC Graduate Manuscript Standards.
- Do not alter the canonical standards artifacts unless intentionally updating
  to a new official UTC edition:
  - `graduate-manuscript-standards-nov-2024.pdf`
  - `graduate-manuscript-standards-nov-2024.sha256`
  - `utc-standards-index.md`

## Branching

- Default branch is `main`.
- Prefer short-lived feature branches for medium/large changes.

## Validation

When editing workflows/docs/repo metadata, ensure:

- GitHub Actions checks pass (`template-checks`, `markdown-lint`).
- Markdown remains lint-clean.

When editing LaTeX/template behavior, also ensure:

- Build succeeds with `latexmk -pdfxe -bibtex Dissertation_Main.tex`.
- Final-mode hyperlink audit passes with `python .\scripts\check_dissertation_hyperlinks.py`.
- Final-mode font audit passes with `python .\scripts\check_dissertation_fonts.py`.
- Preliminary-pages audit passes with `python .\scripts\check_dissertation_prelim_contract.py`.
- Abstract-cap audit passes with `python .\scripts\check_dissertation_abstract_cap.py`.
- TOC sentinel audit passes with `python .\scripts\check_dissertation_toc_contract.py`.
- Page-geometry sentinel audit passes with `python .\scripts\check_dissertation_page_geometry.py`.

## Commit guidance

- Keep commits small and reviewable.
- Use clear, scoped commit messages.
