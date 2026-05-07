# AGENTS.md

Guidance for Codex/Cursor (and any other automated or human “agent”) working in this repository.

This repo contains a University of Tennessee at Chattanooga (UTC) dissertation LaTeX project. The primary objective is **strict compliance with the UTC Graduate Manuscript Standards (Nov 2024)** while keeping the editing workflow stable (MiKTeX + `latexmk` + GitHub sync). The agent should treat formatting requirements as invariants.

---

## Golden rules (do not break these)

1. **Do not change dissertation content** (meaning/wording) unless the user explicitly requests content edits. Formatting changes are allowed.
2. **Follow UTC Manuscript Standards** as the source of truth for formatting (margins, pagination, headings, fonts, etc.).
3. **Final-submission PDFs must have no active hyperlinks** (no clickable URLs, DOI links, etc.). Draft PDFs may allow links if helpful, but final must disable them.
4. **Prefer structural pagination** (e.g., `\pagenumbering{roman}` to `\pagenumbering{arabic}`) and page-style suppression for the committee page number. Do not introduce new ad-hoc `\setcounter` hacks unless there is no structural alternative; if one is used, add a short comment explaining why.
5. **Keep changes small and reviewable**: one logical fix per branch/commit when possible.

---

## Standards source files

- Treat `graduate-manuscript-standards-nov-2024.pdf` as the canonical standards artifact tracked by this repo.
- Keep `utc-standards-index.md` and `graduate-manuscript-standards-nov-2024.sha256` in sync with that PDF.
- If the standards PDF is replaced/updated, refresh the checksum and index notes in the same commit.

---

## Formatting invariants

- Do not manually insert `\vspace` to tune heading spacing; use the `titlesec` rules in `Dissertation_Main.tex`.
- Captions, footnotes, lists, and block quotes are forced to UTC-compliant single spacing in the preamble; do not override them locally.
- Caption punctuation/placement and float spacing are set globally (hang format, space separator, figure captions below and table titles above, float gaps). Do not override locally.
- LIST OF SYMBOLS: format entries as “symbol, definition” (comma + space between).
- DOI/URL in REFERENCES are plain text only (no `\href`/`\url` in bib output).
- Prefer `\UTCFigure`/`\UTCTable` (and `\UTCFigureS`/`\UTCTableS`) wrappers to keep caption placement compliant.

---

## Repo structure (chapters)

- Keep `Dissertation_Main.tex` **lean**: preamble + front matter + the `\include{...}` list + back matter.
- Put each numbered chapter in its own file under `chapters/`, e.g. `chapters/ch03_methodology.tex`.
- Include chapters with `\include{chapters/ch03_methodology}` (do **not** add `.tex`).
- Chapter files must **not** contain `\documentclass`, `\usepackage`, `\begin{document}`, `\end{document}`, `\pagenumbering`, or bibliography/appendix/vita code.

Tip (drafting): you can speed up compiles by adding something like:
`\includeonly{chapters/ch03_methodology}`
near the top of `Dissertation_Main.tex` (comment it back out for full builds).

---

## Build + verify (required after any formatting change)

### Build command (Windows, PowerShell)

Run from repo root:

```powershell
latexmk -pdfxe -bibtex Dissertation_Main.tex
```

(Uses XeLaTeX; required for system fonts like Times New Roman / Calibri.)

Install the pinned rendered-PDF audit dependencies with:

```powershell
python -m pip install -r requirements-audits.txt
```

### Always check the log for problems

After building, scan `Dissertation_Main.log` for:

- `LaTeX Error`
- `Undefined references`
- `Overfull \hbox` (can indicate margin violations)
- `Underfull \hbox` (usually minor, but still review)

### Hyperlink audit (final mode)

For **final submission PDFs**, use the rendered-PDF hyperlink audit script as
the primary check.

Run in PowerShell:

```powershell
python .\scripts\check_dissertation_hyperlinks.py
```

- If it passes, the PDF contains no live links or PDF annotations.
- If it fails, the PDF is **not** acceptable for final submission.

### Font audit (final mode)

UTC requires **Times New Roman or Calibri (11 or 12 pt)** throughout the document text.

- Run:

```powershell
python .\scripts\check_dissertation_fonts.py
```

- The default policy is `refs/editorial_audit/dissertation_font_policy.yml`.
- Use Foxit/Acrobat “Document Properties → Fonts” only as a manual spot-check.
- If fonts show Latin Modern / Computer Modern for body text, that is noncompliant and must be corrected.

### Preliminary-pages audit

Run:

```powershell
python .\scripts\check_dissertation_prelim_contract.py
```

- The default policy is `refs/editorial_audit/dissertation_prelim_contract_policy.yml`.
- This is the primary rendered-PDF check for Roman prelim sequence, suppressed
  printed `i`, bottom-centered prelim numerals, the UTC-sample title-page
  spacer family, title-page degree phrase, and optional copyright-page
  handling.

### Abstract-cap audit

Run:

```powershell
python .\scripts\check_dissertation_abstract_cap.py
```

- The default policy is `refs/editorial_audit/dissertation_abstract_policy.yml`.
- This is the primary rendered-PDF check for heading-delimited abstract
  extraction and UTC's dissertation abstract cap.

### TOC sentinel audit

Run:

```powershell
python .\scripts\check_dissertation_toc_contract.py
```

- The default policy is `refs/editorial_audit/dissertation_toc_contract_policy.yml`.
- This is the primary rendered-PDF check for template-sized TOC sentinels whose
  rendered page labels must match the current body pages.

### Page-geometry sentinel audit

Run:

```powershell
python .\scripts\check_dissertation_page_geometry.py
```

- The default policy is `refs/editorial_audit/dissertation_page_geometry_policy.yml`.
- This is the primary rendered-PDF check for a small set of inch-based page-family
  geometry sentinels before opening the heavier structural/rendered margin stack.

### Structural margin audit

Run:

```powershell
python .\scripts\check_dissertation_margin_structural.py
```

- The default policy is `refs/editorial_audit/dissertation_margin_structural_policy.yml`.
- This is the broader rendered-PDF check for reusable body-box bounds, footer/page-number
  placement, and no-running-header/footer invariants.

### Margin proof overlay

Run:

```powershell
python .\scripts\build_dissertation_margin_proof_overlay.py
```

- The default output is `dissertation_margin_proof_overlay_current.pdf`.
- The generator consumes the existing page-geometry, structural-margin, and TOC
  policies to build human-verifiable rendered proof pages.
- Treat this as required validation output for margin closeout, but do not
  confuse it with a manuscript-specific exact-margin lock stack.

### Exact-margin audit

Run:

```powershell
python .\scripts\audit_dissertation_margin_exact.py
```

- The default policy is `refs/editorial_audit/dissertation_margin_exact_policy.yml`.
- This is a separate second-phase rendered exact-margin lane for the shipped
  template families only.
- Do not fold this script into default public-template CI unless the repo
  policy is explicitly changed to make manuscript-specific exactness part of the
  baseline contract.

---

## UTC non-negotiables (high level)

The agent must preserve/implement these behaviors:

- **Margins**: 1 inch on all sides for body pages; special pages/section starts may require **2 inches of white space at top** for the first line of a major heading.
- **Final PDF links**: no active URL hyperlinks in FINAL submission PDFs (URLs may appear as plain text).
- **Page numbers**:
  - Preliminary pages: **roman numerals**, lower-case, centered at bottom.
  - Committee/approval page is page **i** but **must not print** the page number.
  - Title page is page **ii** and **must print** `ii`.
  - Main text uses **arabic** page numbers starting at 1 on Chapter 1.
- **Committee/approval page content**: start with the dissertation title at the 2" top margin; do not include an “Approved:” label line.
- **Page number placement**: bottom-center with required bottom whitespace on all numbered pages.
- **No running headers** (no chapter title headers, etc.).
- **Section-start spacing**: major headings (ABSTRACT, ACKNOWLEDGEMENTS, TABLE OF CONTENTS, CHAPTER pages, REFERENCES, APPENDIX divider pages, VITA) need the UTC-specified top spacing and blank lines between heading/title/body.
- **Abstract cap**: dissertation abstracts must remain at or below 350 words in
  the rendered preliminary-page PDF surface.
- **TOC/list exactness**: rendered TOC/list sentinel entries must match the live
  body-page labels, and appendix TOC entries must point to divider pages.
- **Page-family geometry**: committee/title/abstract/chapter/reference opener
  families must hold the 2-inch top contract, appendix divider families must
  remain centered, and ordinary numbered body pages must keep bottom-centered
  page numbers with about 1 inch of bottom white space.
- **Structural margins**: rendered text must remain inside the 1-inch left/right
  body box, numbered pages must keep clean footer bands, and running
  headers/footers are not permitted.
- **Margin proof artifact**: build the rendered proof overlay from the shared
  generic policies whenever margin validation is part of the turn.
- **REFERENCES**: entries single-spaced; gap between entries equals the double-spaced baseline (`\bibitemsep=\UTCdblskip-\baselineskip` after `\singlespacing` with `\itemsep` set); no debug `\typeout`.

If any change risks breaking these rules, the agent should stop and surface the risk to the user instead of making a “best guess” silent change.

---

## Git workflow rules

### Branching

- Never do large formatting work directly on the default branch (`main`).
- Use a short-lived feature branch per fix, e.g.:
  - `pagination-fixes`
  - `toc-references-pagefix`
  - `chapter-heading-spacing`

### Commits

- Prefer **small commits** with specific messages, e.g.:
  - `format: fix references TOC page number`
  - `format: enforce 2-inch top spacing on chapter pages`
  - `docs: add AGENTS + README`

### Do not commit build artifacts

Unless the user explicitly requests otherwise, do **not** commit:

- `*.aux *.bbl *.blg *.lof *.lot *.toc *.out *.xdv *.fdb_latexmk *.fls *.synctex.gz *.log`
- PDFs are optional; treat as *release artifacts*, not source, **except** the canonical tracked standards PDF (`graduate-manuscript-standards-nov-2024.pdf`).

If build artifacts are currently being committed, recommend adding/updating `.gitignore`.

---

## Scope & sequencing (timeline awareness)

- **Before the defense or submission deadline**: prioritize
  **structural/pagination** and **hard compliance** items that would be
  disruptive later, such as page numbering, ToC/LoF/LoT correctness, heading
  spacing rules, and margin safety.
- **After the defense or after the hard formatting deadline**: handle
  polish/cleanup items such as minor spacing cosmetics, optional refinements,
  and stylistic improvements.

---

## Safety checks before pushing

Before any `git push`:

1. `git status` is clean (only intended files staged).
2. Build succeeded with `latexmk`.
3. Final-mode hyperlink audit passes.
4. Final-mode font audit passes.
5. Preliminary-pages audit passes.
6. Abstract-cap audit passes.
7. TOC sentinel audit passes.
8. Page-geometry sentinel audit passes.
9. Structural margin audit passes.
10. Margin proof overlay builds successfully.
11. No new margin problems (watch for `Overfull \hbox`).
12. GitHub Actions checks are passing (`Template CI`, `Markdown Lint`) when workflows are touched.

When any template rule changes, update AGENTS.md in the same PR/commit so the agent instructions don't drift.
