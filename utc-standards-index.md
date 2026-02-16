# UTC Standards Index

Canonical standards artifact tracked in this repo:
- `graduate-manuscript-standards-nov-2024.pdf`

Companion integrity/provenance artifact:
- `graduate-manuscript-standards-nov-2024.sha256`

Official URL:
- https://www.utc.edu/sites/default/files/2024-11/graduate-manuscript-standards-nov-2024.pdf

Edition/date:
- Eighth Edition, November 1, 2024

Template-facing non-negotiables mapped from the standards:
- Fonts: Times New Roman or Calibri (11 or 12 pt) for body text.
- Margins: 1 inch body margins, with 2-inch top spacing for major heading/section-start pages.
- Pagination: lowercase Roman for preliminary pages, Arabic starting at Chapter 1 page 1.
- Committee page: assigned page `i` with no printed numeral.
- Page-number placement: bottom-center with required bottom whitespace.
- No running headers/footers.
- Final submission PDF must not contain active URL hyperlinks.
- References heading/page spacing and entry spacing must follow UTC examples.
- TOC/LoT/LoF and chapter/section heading formatting must remain UTC-compliant.

Local interpretation notes used by this template:
- Committee page starts with the title at the 2-inch top margin and omits an `Approved:` label line.
- Preliminary optional heading uses `ACKNOWLEDGEMENTS` spelling consistently in this template.
- DOI/URL fields are emitted as plain text in references to keep final PDFs non-clickable.
- Appendix entries in the TOC use divider-page numbers via `\\UTCAppendixDivider`.

Maintenance workflow:
1. Replace `graduate-manuscript-standards-nov-2024.pdf` only when adopting a new official UTC edition.
2. Regenerate checksum:
   `sha256sum graduate-manuscript-standards-nov-2024.pdf > graduate-manuscript-standards-nov-2024.sha256`
3. Update this index for edition/date and any changed requirement interpretations.
4. Commit all three files in one commit.
