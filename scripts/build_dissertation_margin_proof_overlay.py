#!/usr/bin/env python3
"""Build a rendered-PDF margin proof overlay from generic template policies."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz


DEFAULT_PAGE_GEOMETRY_POLICY = Path("refs/editorial_audit/dissertation_page_geometry_policy.yml")
DEFAULT_STRUCTURAL_POLICY = Path("refs/editorial_audit/dissertation_margin_structural_policy.yml")
DEFAULT_TOC_POLICY = Path("refs/editorial_audit/dissertation_toc_contract_policy.yml")
DEFAULT_OUT = Path("dissertation_margin_proof_overlay_current.pdf")
POINTS_PER_INCH = 72.0


@dataclass(frozen=True)
class HeadingTopCheck:
    name: str
    required_patterns: tuple[str, ...]
    phrase: str
    case_sensitive: bool


@dataclass(frozen=True)
class AppendixDividerCheck:
    name: str
    required_patterns: tuple[str, ...]
    appendix_phrase: str
    title_phrase: str
    optional: bool
    case_sensitive: bool


@dataclass(frozen=True)
class PageNumberPlacementCheck:
    name: str
    required_patterns: tuple[str, ...]
    expected_label: str
    case_sensitive: bool


@dataclass(frozen=True)
class GeometryPolicy:
    heading_top_checks: tuple[HeadingTopCheck, ...]
    appendix_divider_checks: tuple[AppendixDividerCheck, ...]
    page_number_checks: tuple[PageNumberPlacementCheck, ...]


@dataclass(frozen=True)
class TocSectionPolicy:
    start_heading: str
    stop_page_headings: tuple[str, ...]


@dataclass(frozen=True)
class TocPolicy:
    toc_section: TocSectionPolicy


@dataclass(frozen=True)
class BodyBoxPolicy:
    left_margin_min_in: float
    right_margin_min_in: float


@dataclass(frozen=True)
class FooterPolicy:
    header_clear_band_in: float
    footer_band_height_in: float


@dataclass(frozen=True)
class StructuralPolicy:
    body_box: BodyBoxPolicy
    footer: FooterPolicy


@dataclass
class SelectedPage:
    physical_page: int
    family_labels: list[str]
    highlight_phrases: list[str]


def _normalize_line(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split()).strip()


def _page_lines(page: fitz.Page) -> list[str]:
    page_label = _normalize_line(str(page.get_label()))
    lines = [_normalize_line(line) for line in page.get_text("text", sort=True).splitlines()]
    return [line for line in lines if line and line != page_label]


def _page_text(page: fitz.Page) -> str:
    return " ".join(_page_lines(page))


def _in_to_pt(value: float) -> float:
    return float(value) * POINTS_PER_INCH


def _load_geometry_policy(path: Path) -> GeometryPolicy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    heading_top_checks = tuple(
        HeadingTopCheck(
            name=str(item["name"]),
            required_patterns=tuple(str(pattern) for pattern in item.get("required_patterns", [])),
            phrase=str(item["phrase"]),
            case_sensitive=bool(item.get("case_sensitive", True)),
        )
        for item in raw.get("heading_top_checks", [])
    )
    appendix_divider_checks = tuple(
        AppendixDividerCheck(
            name=str(item["name"]),
            required_patterns=tuple(str(pattern) for pattern in item.get("required_patterns", [])),
            appendix_phrase=str(item["appendix_phrase"]),
            title_phrase=str(item["title_phrase"]),
            optional=bool(item.get("optional", False)),
            case_sensitive=bool(item.get("case_sensitive", True)),
        )
        for item in raw.get("appendix_divider_checks", [])
    )
    page_number_checks = tuple(
        PageNumberPlacementCheck(
            name=str(item["name"]),
            required_patterns=tuple(str(pattern) for pattern in item.get("required_patterns", [])),
            expected_label=str(item["expected_label"]),
            case_sensitive=bool(item.get("case_sensitive", True)),
        )
        for item in raw.get("page_number_checks", [])
    )
    return GeometryPolicy(
        heading_top_checks=heading_top_checks,
        appendix_divider_checks=appendix_divider_checks,
        page_number_checks=page_number_checks,
    )


def _load_structural_policy(path: Path) -> StructuralPolicy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    body_box_raw = raw.get("body_box", {})
    footer_raw = raw.get("footer", {})
    return StructuralPolicy(
        body_box=BodyBoxPolicy(
            left_margin_min_in=float(body_box_raw.get("left_margin_min_in", 1.0)),
            right_margin_min_in=float(body_box_raw.get("right_margin_min_in", 1.0)),
        ),
        footer=FooterPolicy(
            header_clear_band_in=float(footer_raw.get("header_clear_band_in", 0.8)),
            footer_band_height_in=float(footer_raw.get("footer_band_height_in", 1.25)),
        ),
    )


def _load_toc_policy(path: Path) -> TocPolicy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    toc_section_raw = raw.get("toc_section", {})
    return TocPolicy(
        toc_section=TocSectionPolicy(
            start_heading=str(toc_section_raw.get("start_heading", "TABLE OF CONTENTS")),
            stop_page_headings=tuple(str(item) for item in toc_section_raw.get("stop_page_headings", [])),
        )
    )


def _find_page(
    pdf: fitz.Document, required_patterns: tuple[str, ...], case_sensitive: bool
) -> tuple[int | None, fitz.Page | None]:
    flags = 0 if case_sensitive else re.IGNORECASE
    for page_index in range(pdf.page_count):
        page = pdf.load_page(page_index)
        text = _page_text(page)
        if all(re.search(pattern, text, flags) for pattern in required_patterns):
            return page_index + 1, page
    return None, None


def _collect_toc_pages(pdf: fitz.Document, policy: TocSectionPolicy) -> list[int]:
    collecting = False
    toc_pages: list[int] = []

    for page_index in range(pdf.page_count):
        page = pdf.load_page(page_index)
        lines = _page_lines(page)
        if not lines:
            continue

        first_line = lines[0]
        if not collecting:
            if policy.start_heading not in lines:
                continue
            collecting = True
        elif first_line in policy.stop_page_headings:
            break

        toc_pages.append(page_index + 1)

    return toc_pages


def _add_selected_page(
    selected: dict[int, SelectedPage], physical_page: int, family_label: str, phrases: list[str]
) -> None:
    page_entry = selected.setdefault(
        physical_page,
        SelectedPage(physical_page=physical_page, family_labels=[], highlight_phrases=[]),
    )
    if family_label not in page_entry.family_labels:
        page_entry.family_labels.append(family_label)
    for phrase in phrases:
        normalized = _normalize_line(phrase)
        if normalized and normalized not in page_entry.highlight_phrases:
            page_entry.highlight_phrases.append(normalized)


def _draw_guides(page: fitz.Page, policy: StructuralPolicy) -> None:
    width = float(page.rect.width)
    height = float(page.rect.height)
    left_margin = _in_to_pt(policy.body_box.left_margin_min_in)
    right_margin = width - _in_to_pt(policy.body_box.right_margin_min_in)
    one_in = _in_to_pt(1.0)
    two_in = _in_to_pt(2.0)
    bottom_one_in = height - _in_to_pt(1.0)
    header_clear = _in_to_pt(policy.footer.header_clear_band_in)
    footer_band = height - _in_to_pt(policy.footer.footer_band_height_in)

    shape = page.new_shape()
    shape.draw_line(fitz.Point(0, one_in), fitz.Point(width, one_in))
    shape.draw_line(fitz.Point(0, two_in), fitz.Point(width, two_in))
    shape.draw_line(fitz.Point(left_margin, 0), fitz.Point(left_margin, height))
    shape.draw_line(fitz.Point(right_margin, 0), fitz.Point(right_margin, height))
    shape.draw_line(fitz.Point(0, bottom_one_in), fitz.Point(width, bottom_one_in))
    shape.finish(color=(0.0, 0.55, 0.0), width=0.8)
    shape.commit()

    band_shape = page.new_shape()
    band_shape.draw_line(fitz.Point(0, header_clear), fitz.Point(width, header_clear))
    band_shape.draw_line(fitz.Point(0, footer_band), fitz.Point(width, footer_band))
    band_shape.finish(color=(0.15, 0.35, 0.75), width=0.6)
    band_shape.commit()

    page.insert_text((12, max(one_in - 6, 10)), "1.00 in top", fontsize=8, color=(0.0, 0.55, 0.0))
    page.insert_text((12, max(two_in - 6, 10)), "2.00 in top", fontsize=8, color=(0.8, 0.1, 0.1))
    page.insert_text((12, max(bottom_one_in - 6, 10)), "1.00 in bottom", fontsize=8, color=(0.0, 0.55, 0.0))


def _draw_phrase_highlights(page: fitz.Page, phrases: list[str]) -> None:
    colors = (
        (0.85, 0.35, 0.0),
        (0.45, 0.0, 0.75),
        (0.0, 0.45, 0.85),
        (0.1, 0.55, 0.1),
    )
    for index, phrase in enumerate(phrases):
        rects = page.search_for(phrase)
        color = colors[index % len(colors)]
        if rects:
            for rect in rects:
                page.draw_rect(rect, color=color, width=0.8)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a rendered-PDF margin proof overlay from generic template policies."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("Dissertation_Main.pdf"),
        help="PDF relative to repo root (default: Dissertation_Main.pdf).",
    )
    parser.add_argument(
        "--page-geometry-policy",
        type=Path,
        default=DEFAULT_PAGE_GEOMETRY_POLICY,
        help=f"Page-geometry policy relative to repo root (default: {DEFAULT_PAGE_GEOMETRY_POLICY}).",
    )
    parser.add_argument(
        "--structural-policy",
        type=Path,
        default=DEFAULT_STRUCTURAL_POLICY,
        help=f"Structural policy relative to repo root (default: {DEFAULT_STRUCTURAL_POLICY}).",
    )
    parser.add_argument(
        "--toc-policy",
        type=Path,
        default=DEFAULT_TOC_POLICY,
        help=f"TOC policy relative to repo root (default: {DEFAULT_TOC_POLICY}).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output PDF relative to repo root (default: {DEFAULT_OUT}).",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    pdf_path = (repo_root / args.pdf).resolve()
    page_geometry_policy = _load_geometry_policy((repo_root / args.page_geometry_policy).resolve())
    structural_policy = _load_structural_policy((repo_root / args.structural_policy).resolve())
    toc_policy = _load_toc_policy((repo_root / args.toc_policy).resolve())
    out_path = (repo_root / args.out).resolve()

    try:
        pdf = fitz.open(pdf_path)
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing PDF: {pdf_path}") from exc
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise SystemExit(f"Failed to open PDF '{pdf_path}': {exc}") from exc

    selected: dict[int, SelectedPage] = {}
    with pdf:
        for check in page_geometry_policy.heading_top_checks:
            physical_page, _ = _find_page(pdf, check.required_patterns, check.case_sensitive)
            if physical_page is not None:
                _add_selected_page(selected, physical_page, check.name, [check.phrase])

        for check in page_geometry_policy.appendix_divider_checks:
            physical_page, _ = _find_page(pdf, check.required_patterns, check.case_sensitive)
            if physical_page is None:
                if check.optional:
                    continue
                raise SystemExit(f"Required appendix divider page family was not found: {check.name}")
            _add_selected_page(
                selected,
                physical_page,
                check.name,
                [check.appendix_phrase, check.title_phrase],
            )

        for check in page_geometry_policy.page_number_checks:
            physical_page, page = _find_page(pdf, check.required_patterns, check.case_sensitive)
            if physical_page is None or page is None:
                raise SystemExit(f"Required page-number sentinel page was not found: {check.name}")
            _add_selected_page(selected, physical_page, check.name, [check.expected_label])

        for physical_page in _collect_toc_pages(pdf, toc_policy.toc_section):
            _add_selected_page(
                selected,
                physical_page,
                "table of contents family",
                [toc_policy.toc_section.start_heading],
            )

    if not selected:
        raise SystemExit("No proof-overlay pages were selected from the active policies.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    source = fitz.open(pdf_path)
    proof = fitz.open()
    for physical_page in sorted(selected):
        page_spec = selected[physical_page]
        proof.insert_pdf(source, from_page=physical_page - 1, to_page=physical_page - 1)
        page = proof[-1]
        _draw_guides(page, structural_policy)
        _draw_phrase_highlights(page, page_spec.highlight_phrases)
        page.insert_text(
            (12, 18),
            f"physical page {physical_page} | " + " | ".join(page_spec.family_labels),
            fontsize=9,
            color=(0.0, 0.0, 0.0),
        )
    proof.save(out_path)
    proof.close()
    source.close()

    print("OK: dissertation margin proof overlay built")
    print(f"- PDF: {pdf_path}")
    print(f"- Page-geometry policy: {args.page_geometry_policy.as_posix()}")
    print(f"- Structural policy: {args.structural_policy.as_posix()}")
    print(f"- TOC policy: {args.toc_policy.as_posix()}")
    print(f"- Output: {out_path}")
    print("- Physical pages: " + ", ".join(str(page) for page in sorted(selected)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
