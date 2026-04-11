# UTC Dissertation Template

[![License](https://img.shields.io/github/license/M-Gage-Plott42/Dissertation_Template?label=License)](LICENSE)
[![Template CI](https://github.com/M-Gage-Plott42/Dissertation_Template/actions/workflows/template-ci.yml/badge.svg)](https://github.com/M-Gage-Plott42/Dissertation_Template/actions/workflows/template-ci.yml)
[![Markdown Lint](https://github.com/M-Gage-Plott42/Dissertation_Template/actions/workflows/markdown-lint.yml/badge.svg)](https://github.com/M-Gage-Plott42/Dissertation_Template/actions/workflows/markdown-lint.yml)
[![Release](https://img.shields.io/github/v/release/M-Gage-Plott42/Dissertation_Template?label=Release)](https://github.com/M-Gage-Plott42/Dissertation_Template/releases)

LaTeX dissertation project aligned to **The University of Tennessee at
Chattanooga (UTC) Graduate Manuscript Standards (Nov 2024)**.

This repo is intended to be the *source of truth* for writing + formatting,
with:

- Local compilation (MiKTeX + XeLaTeX)
- Git/GitHub sync for working across machines
- A draft/final toggle to disable hyperlinks in submission PDFs

## UTC standards source files

- `graduate-manuscript-standards-nov-2024.pdf` is the canonical UTC
  formatting source used by this template.
- `utc-standards-index.md` summarizes edition, key requirements used by the
  template, and local interpretation notes.
- `graduate-manuscript-standards-nov-2024.sha256` stores the checksum for
  integrity and provenance.

When updating the standards PDF, update all three files in the same commit.

---

## Requirements (Windows)

- **MiKTeX** (with XeLaTeX)
- **Perl** (required for `latexmk` in MiKTeX on Windows)
- `latexmk` available on PATH (MiKTeX installs it)
- Optional: a PDF viewer that can inspect fonts (Foxit/Adobe)

---

## Build

From the repo root:

```powershell
latexmk -pdfxe -bibtex Dissertation_Main.tex
```

Note: this MiKTeX latexmk build does not accept `-usebiber`; `-bibtex` still
invokes biber automatically for `biblatex` projects.

Common helpful commands:

```powershell
# Clean build artifacts
latexmk -c

# Force a full rebuild if something gets "stuck"
latexmk -pdfxe -bibtex -f Dissertation_Main.tex
```

---

## Draft vs final submission PDFs

This template includes a toggle (see `Dissertation_Main.tex`) to control
hyperlink behavior:

- **Draft mode (`\UTCFinalfalse`)**: hyperlinks may be enabled for
  convenience while writing.
- **Final mode (`\UTCFinaltrue`)**: hyperlinks must be disabled (UTC does not
  accept active URL links in the submitted PDF).

### Final PDF hyperlink audit

Primary check:

```powershell
python .\scripts\check_dissertation_hyperlinks.py
```

This audit inspects the rendered PDF for live link objects and annotations.
Use it instead of raw `/URI` grep.

---

## Submission sanity checks

- FINAL build has no active URL links (per UTC).
- Preliminary-pages audit passes with
  `python .\scripts\check_dissertation_prelim_contract.py`.
- Abstract-cap audit passes with
  `python .\scripts\check_dissertation_abstract_cap.py`.
- TOC sentinel audit passes with
  `python .\scripts\check_dissertation_toc_contract.py`.
- TOC page numbers match the actual page numbers in the PDF.
- Appendix entries in the TOC list divider page numbers.
- Committee/approval page starts with the title at the 2" top margin; no
  `Approved:` label line.

## Preliminary-pages audit

Primary check:

```powershell
python .\scripts\check_dissertation_prelim_contract.py
```

This audit checks the rendered PDF for:

- lower-case Roman prelim labels through the page before Chapter 1 page `1`
- suppressed printed numeral on page `i`
- bottom-centered prelim numerals on the remaining prelim pages
- a configurable degree-name phrase on the title page
- optional copyright-page presence and centered placement

Policy lives in `refs/editorial_audit/dissertation_prelim_contract_policy.yml`.
When adapting the template for a real manuscript, update the degree phrase and
copyright-page toggle there to match the intended submission state.

---

## Abstract-cap audit

Primary check:

```powershell
python .\scripts\check_dissertation_abstract_cap.py
```

This audit checks the rendered PDF for:

- `ABSTRACT` as the start heading
- a configurable set of stop headings for the next preliminary major page
- heading-delimited rendered-text extraction only
- UTC's dissertation abstract cap of 350 words by default

Policy lives in `refs/editorial_audit/dissertation_abstract_policy.yml`.
When adapting the template for another manuscript flow, update the stop
headings and max-word cap there rather than hard-coding page windows in the
script.

---

## TOC sentinel audit

Primary check:

```powershell
python .\scripts\check_dissertation_toc_contract.py
```

This audit checks the rendered PDF for:

- a live TOC section extracted from the rendered PDF rather than `.tex` tokens
- template-sized TOC sentinels only: `ABSTRACT`, `LIST OF TABLES`,
  `LIST OF FIGURES`, first numbered chapter, first appendix divider if
  present, and `VITA`
- TOC entries whose rendered page labels match the current body-page labels
- populated list-of-tables and list-of-figures pages via their sentinel body
  patterns

Policy lives in `refs/editorial_audit/dissertation_toc_contract_policy.yml`.
Keep this expectations surface small and template-generic; deeper manuscript-
specific chapter/table/figure inventories belong in dissertation-local audits,
not in the public template.

---

## Font compliance

UTC requires **Times New Roman or Calibri (11 or 12 pt)** for document text.

Primary check:

```powershell
python .\scripts\check_dissertation_fonts.py
```

This audit verifies embedded rendered PDF font families against the policy in
`refs/editorial_audit/dissertation_font_policy.yml`.

Manual spot-check after the script still makes sense:

- "Document Properties -> Fonts" shows Times New Roman or Calibri embedded
  for body text.
- Small exceptions may exist for math or monospace code, but the *main body
  font* should comply.

CI note:

- GitHub Actions uses a compile-only Linux fallback font (`TeX Gyre Termes`)
  because the runner does not ship Times New Roman or Calibri.
- The CI workflow therefore uses the CI-specific policy file
  `refs/editorial_audit/dissertation_font_policy_ci.yml`.
- Local/final dissertation compliance still uses the default policy and UTC's
  approved fonts.

---

## Bibliography workflow (Zotero recommended)

Recommended setup:

1. Install Zotero.
2. Install **Better BibTeX** for Zotero.
3. Create a *single* library collection for your dissertation sources.
4. Set Better BibTeX to automatically export to a `.bib` file tracked in this
   repo (e.g., `citations.bib`).

Tips:

- Use citation keys that are stable and human-readable (e.g.,
  `Ramm2005LeastSquares`).
- Avoid editing the exported `.bib` by hand when possible; make corrections in
  Zotero and re-export.

---

## Suggested repo structure

A common structure (adjust to your project):

```text
Dissertation_Main.tex
chapters/
  ch01_intro.tex
  ch02_lit_review.tex
  ch03_methodology.tex
  ch04_results.tex
  ch05_discussion.tex
  ch06_conclusion.tex
  ch07_future_work.tex
figures/
tables/
citations.bib
```

Chapters are included from `Dissertation_Main.tex` via
`\include{chapters/<file>}` so the main file stays lean and merge-friendly.

---

## Git workflow (recommended)

Use small feature branches and merge into `main`:

```powershell
git switch -c <branch-name>
# edit files
git add <files>
git commit -m "format: <what changed>"
git push -u origin <branch-name>
```

Then merge into `main` (either via PR on GitHub or via CLI).

---

## License

This repository is licensed under the MIT License. See `LICENSE`.

## Repository metadata

- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Notes

- Formatting rules come from UTC Graduate School standards; when in doubt,
  follow the standards over LaTeX defaults.
- Keep changes incremental; recompile frequently.
- When the workflow changes (compile command, branch flow, toggle names),
  update `README.md` in the same commit/PR.
