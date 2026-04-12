# UTC Standards Index

Canonical standards artifact tracked in this repo:

- `graduate-manuscript-standards-nov-2024.pdf`

Companion integrity/provenance artifact:

- `graduate-manuscript-standards-nov-2024.sha256`

Official URL:

- [UTC Graduate Manuscript Standards (Nov 2024)](
  https://www.utc.edu/sites/default/files/2024-11/graduate-manuscript-standards-nov-2024.pdf
  )

Edition/date:

- Eighth Edition, November 1, 2024

Template-facing non-negotiables mapped from the standards:

- Fonts: Times New Roman or Calibri (11 or 12 pt) for body text.
- Margins: 1 inch body margins, with 2-inch top spacing for major
  heading/section-start pages.
- Pagination: lowercase Roman for preliminary pages, Arabic starting at
  Chapter 1 page 1.
- Committee page: assigned page `i` with no printed numeral.
- Page-number placement: bottom-center with required bottom whitespace.
- No running headers/footers.
- Final submission PDF must not contain active URL hyperlinks.
- TOC / LoT / LoF entries must match the rendered document, including appendix
  divider-page numbering in the TOC.
- Key rendered page families should hold the UTC geometry contract: 2-inch
  opener spacing where required, centered appendix divider sheets, and
  bottom-centered page numbers with about 1 inch of bottom white space.
- The reusable structural margin contract is broader than the page-family
  sentinels: rendered text should stay inside the 1-inch left/right body box,
  numbered pages should keep clean footer bands, and running headers/footers
  are not permitted.
- The template validation workflow also generates a rendered proof overlay from
  the generic page-geometry, structural-margin, and TOC policies so margin
  guides can be visually checked without promoting a dissertation-specific
  exact-margin lock stack into the public template baseline.
- A separate opt-in rendered exact-margin audit may be used for second-phase
  closeout of the shipped template families, but it is intentionally kept
  outside the default public-template CI contract.
- References heading/page spacing and entry spacing must follow UTC examples.
- TOC/LoT/LoF and chapter/section heading formatting must remain UTC-compliant.

Local interpretation notes used by this template:

- Committee page starts with the title at the 2-inch top margin and omits an
  `Approved:` label line.
- Preliminary optional heading uses `ACKNOWLEDGEMENTS` spelling consistently
  in this template.
- DOI/URL fields are emitted as plain text in references to keep final PDFs
  non-clickable.
- Appendix entries in the TOC use divider-page numbers via
  `\\UTCAppendixDivider`.

Maintenance workflow:

1. Replace `graduate-manuscript-standards-nov-2024.pdf` only when adopting a
   new official UTC edition.
2. Regenerate checksum:

   ```bash
   sha256sum graduate-manuscript-standards-nov-2024.pdf > graduate-manuscript-standards-nov-2024.sha256
   ```

3. Update this index for edition/date and any changed requirement
   interpretations.
4. Commit all three files in one commit.
