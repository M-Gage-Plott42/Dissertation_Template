# Dissertation_Main

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Template CI](https://github.com/M-Gage-Plott42/Dissertation_Template/actions/workflows/template-ci.yml/badge.svg)](https://github.com/M-Gage-Plott42/Dissertation_Template/actions/workflows/template-ci.yml)
[![Markdown Lint](https://github.com/M-Gage-Plott42/Dissertation_Template/actions/workflows/markdown-lint.yml/badge.svg)](https://github.com/M-Gage-Plott42/Dissertation_Template/actions/workflows/markdown-lint.yml)

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

Quick check (PowerShell):

```powershell
Select-String -Pattern "/URI" -Path .\Dissertation_Main.pdf
```

If no matches: good.
If matches appear: the PDF contains active links and must be fixed before
submission.

---

## Submission sanity checks

- FINAL build has no active URL links (per UTC).
- TOC page numbers match the actual page numbers in the PDF.
- Appendix entries in the TOC list divider page numbers.
- Committee/approval page starts with the title at the 2" top margin; no
  `Approved:` label line.

---

## Font compliance

UTC requires **Times New Roman or Calibri (11 or 12 pt)** for document text.

After compiling, verify in your PDF viewer:

- "Document Properties -> Fonts" shows Times New Roman or Calibri embedded
  for body text.
- Small exceptions may exist for math or monospace code, but the *main body
  font* should comply.

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

Use small feature branches and merge into `public-template-clean`:

```powershell
git switch -c <branch-name>
# edit files
git add <files>
git commit -m "format: <what changed>"
git push -u origin <branch-name>
```

Then merge into `public-template-clean` (either via PR on GitHub or via CLI).

---

## License

This repository is licensed under the MIT License. See `LICENSE`.

## Notes

- Formatting rules come from UTC Graduate School standards; when in doubt,
  follow the standards over LaTeX defaults.
- Keep changes incremental; recompile frequently.
- When the workflow changes (compile command, branch flow, toggle names),
  update `README.md` in the same commit/PR.
