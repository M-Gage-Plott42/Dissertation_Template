#!/usr/bin/env python3
"""Run a separate rendered exact-margin audit for the UTC template."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz


DEFAULT_POLICY = Path("refs/editorial_audit/dissertation_margin_exact_policy.yml")
POINTS_PER_INCH = 72.0


@dataclass(frozen=True)
class PhraseTopCheck:
    name: str
    required_patterns: tuple[str, ...]
    phrase: str
    top_range_in: tuple[float, float]
    case_sensitive: bool


@dataclass(frozen=True)
class GapCheck:
    name: str
    required_patterns: tuple[str, ...]
    upper_phrase: str
    lower_phrase: str
    gap_range_in: tuple[float, float]
    case_sensitive: bool


@dataclass(frozen=True)
class DividerCenterCheck:
    name: str
    required_patterns: tuple[str, ...]
    appendix_phrase: str
    title_phrase: str
    center_x_range_in: tuple[float, float]
    center_y_range_in: tuple[float, float]
    optional: bool
    case_sensitive: bool


@dataclass(frozen=True)
class FooterPlacementPolicy:
    footer_band_height_in: float
    bottom_whitespace_range_in: tuple[float, float]
    center_x_tolerance_in: float
    suppressed_page_labels: tuple[str, ...]


@dataclass(frozen=True)
class ExactMarginPolicy:
    purpose: str
    heading_top_checks: tuple[PhraseTopCheck, ...]
    gap_checks: tuple[GapCheck, ...]
    appendix_divider_checks: tuple[DividerCenterCheck, ...]
    footer: FooterPlacementPolicy


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split()).strip()


def _page_lines(page: fitz.Page) -> list[str]:
    page_label = _normalize_text(str(page.get_label()))
    lines = [_normalize_text(line) for line in page.get_text("text", sort=True).splitlines()]
    return [line for line in lines if line and line != page_label]


def _page_text(page: fitz.Page) -> str:
    return " ".join(_page_lines(page))


def _pt_to_in(value: float) -> float:
    return float(value) / POINTS_PER_INCH


def _in_to_pt(value: float) -> float:
    return float(value) * POINTS_PER_INCH


def _union_rects(rects: list[fitz.Rect]) -> fitz.Rect | None:
    if not rects:
        return None
    rect = fitz.Rect(rects[0])
    for other in rects[1:]:
        rect |= other
    return rect


def _search_rect(page: fitz.Page, phrase: str) -> fitz.Rect | None:
    return _union_rects(page.search_for(phrase))


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


def _load_policy(path: Path) -> ExactMarginPolicy:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing policy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Policy file is not valid JSON/YAML-1.2 JSON subset: {exc}") from exc

    heading_top_checks = tuple(
        PhraseTopCheck(
            name=str(item["name"]),
            required_patterns=tuple(str(pattern) for pattern in item.get("required_patterns", [])),
            phrase=str(item["phrase"]),
            top_range_in=(float(item["top_range_in"][0]), float(item["top_range_in"][1])),
            case_sensitive=bool(item.get("case_sensitive", True)),
        )
        for item in raw.get("heading_top_checks", [])
    )
    gap_checks = tuple(
        GapCheck(
            name=str(item["name"]),
            required_patterns=tuple(str(pattern) for pattern in item.get("required_patterns", [])),
            upper_phrase=str(item["upper_phrase"]),
            lower_phrase=str(item["lower_phrase"]),
            gap_range_in=(float(item["gap_range_in"][0]), float(item["gap_range_in"][1])),
            case_sensitive=bool(item.get("case_sensitive", True)),
        )
        for item in raw.get("gap_checks", [])
    )
    appendix_divider_checks = tuple(
        DividerCenterCheck(
            name=str(item["name"]),
            required_patterns=tuple(str(pattern) for pattern in item.get("required_patterns", [])),
            appendix_phrase=str(item["appendix_phrase"]),
            title_phrase=str(item["title_phrase"]),
            center_x_range_in=(float(item["center_x_range_in"][0]), float(item["center_x_range_in"][1])),
            center_y_range_in=(float(item["center_y_range_in"][0]), float(item["center_y_range_in"][1])),
            optional=bool(item.get("optional", False)),
            case_sensitive=bool(item.get("case_sensitive", True)),
        )
        for item in raw.get("appendix_divider_checks", [])
    )
    footer_raw = raw.get("footer", {})
    return ExactMarginPolicy(
        purpose=str(raw.get("purpose", "")),
        heading_top_checks=heading_top_checks,
        gap_checks=gap_checks,
        appendix_divider_checks=appendix_divider_checks,
        footer=FooterPlacementPolicy(
            footer_band_height_in=float(footer_raw.get("footer_band_height_in", 1.25)),
            bottom_whitespace_range_in=(
                float(footer_raw.get("bottom_whitespace_range_in", [0.96, 1.00])[0]),
                float(footer_raw.get("bottom_whitespace_range_in", [0.96, 1.00])[1]),
            ),
            center_x_tolerance_in=float(footer_raw.get("center_x_tolerance_in", 0.03)),
            suppressed_page_labels=tuple(
                str(item) for item in footer_raw.get("suppressed_page_labels", ["i"])
            ),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a separate rendered exact-margin audit for the UTC template."
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
        "--policy",
        type=Path,
        default=DEFAULT_POLICY,
        help=f"Policy relative to repo root (default: {DEFAULT_POLICY}).",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    pdf_path = (repo_root / args.pdf).resolve()
    policy_path = (repo_root / args.policy).resolve()
    policy = _load_policy(policy_path)

    try:
        pdf = fitz.open(pdf_path)
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing PDF: {pdf_path}") from exc
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise SystemExit(f"Failed to open PDF '{pdf_path}': {exc}") from exc

    findings: list[str] = []
    measurements: list[str] = []
    checked = 0
    numbered_pages_checked = 0

    with pdf:
        for check in policy.heading_top_checks:
            physical_page, page = _find_page(pdf, check.required_patterns, check.case_sensitive)
            if page is None or physical_page is None:
                findings.append(f"required page family '{check.name}' was not found in the rendered PDF")
                continue
            rect = _search_rect(page, check.phrase)
            if rect is None:
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} is missing phrase '{check.phrase}'"
                )
                continue
            top_in = _pt_to_in(rect.y0)
            if not (check.top_range_in[0] <= top_in <= check.top_range_in[1]):
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} has top "
                    f"{top_in:.4f} in outside {check.top_range_in[0]:.4f}-{check.top_range_in[1]:.4f} in"
                )
                continue
            measurements.append(
                f"{check.name}: physical page {physical_page}, top {top_in:.4f} in"
            )
            checked += 1

        for check in policy.gap_checks:
            physical_page, page = _find_page(pdf, check.required_patterns, check.case_sensitive)
            if page is None or physical_page is None:
                findings.append(f"required page family '{check.name}' was not found in the rendered PDF")
                continue
            upper_rect = _search_rect(page, check.upper_phrase)
            lower_rect = _search_rect(page, check.lower_phrase)
            if upper_rect is None or lower_rect is None:
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} is missing one or more anchor phrases"
                )
                continue
            gap_in = _pt_to_in(lower_rect.y0 - upper_rect.y1)
            if not (check.gap_range_in[0] <= gap_in <= check.gap_range_in[1]):
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} has gap "
                    f"{gap_in:.4f} in outside {check.gap_range_in[0]:.4f}-{check.gap_range_in[1]:.4f} in"
                )
                continue
            measurements.append(
                f"{check.name}: physical page {physical_page}, gap {gap_in:.4f} in"
            )
            checked += 1

        for check in policy.appendix_divider_checks:
            physical_page, page = _find_page(pdf, check.required_patterns, check.case_sensitive)
            if page is None or physical_page is None:
                if check.optional:
                    measurements.append(f"{check.name}: not present, skipped")
                    continue
                findings.append(f"required page family '{check.name}' was not found in the rendered PDF")
                continue
            appendix_rect = _search_rect(page, check.appendix_phrase)
            title_rect = _search_rect(page, check.title_phrase)
            if appendix_rect is None or title_rect is None:
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} is missing one or more anchor phrases"
                )
                continue
            union_rect = _union_rects([appendix_rect, title_rect])
            if union_rect is None:
                findings.append(f"page family '{check.name}' on physical page {physical_page} has no measurable block")
                continue
            center_x_in = _pt_to_in((union_rect.x0 + union_rect.x1) / 2.0)
            center_y_in = _pt_to_in((union_rect.y0 + union_rect.y1) / 2.0)
            if not (check.center_x_range_in[0] <= center_x_in <= check.center_x_range_in[1]):
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} has center x "
                    f"{center_x_in:.4f} in outside {check.center_x_range_in[0]:.4f}-{check.center_x_range_in[1]:.4f} in"
                )
                continue
            if not (check.center_y_range_in[0] <= center_y_in <= check.center_y_range_in[1]):
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} has center y "
                    f"{center_y_in:.4f} in outside {check.center_y_range_in[0]:.4f}-{check.center_y_range_in[1]:.4f} in"
                )
                continue
            measurements.append(
                f"{check.name}: physical page {physical_page}, center ({center_x_in:.4f}, {center_y_in:.4f}) in"
            )
            checked += 1

        footer_band_height_pt = _in_to_pt(policy.footer.footer_band_height_in)
        center_tolerance_pt = _in_to_pt(policy.footer.center_x_tolerance_in)

        for page_index in range(pdf.page_count):
            page = pdf.load_page(page_index)
            page_label = _normalize_text(str(page.get_label()))
            if page_label in policy.footer.suppressed_page_labels:
                continue
            footer_band_start_pt = float(page.rect.height) - footer_band_height_pt
            page_center_x_pt = float(page.rect.width) / 2.0
            footer_words = [
                item for item in page.get_text("words", sort=True)
                if _normalize_text(str(item[4])) and float(item[1]) >= footer_band_start_pt
            ]
            normalized_words = [
                {
                    "x0": float(item[0]),
                    "y0": float(item[1]),
                    "x1": float(item[2]),
                    "y1": float(item[3]),
                    "text": _normalize_text(str(item[4])),
                }
                for item in footer_words
            ]
            number_candidates = [word for word in normalized_words if word["text"] == page_label]
            physical_page = page_index + 1
            if not number_candidates:
                findings.append(
                    f"physical page {physical_page} (label {page_label}) is missing its footer page-number token"
                )
                continue
            selected_page_number = min(
                number_candidates,
                key=lambda word: abs(((word["x0"] + word["x1"]) / 2.0) - page_center_x_pt),
            )
            center_x_pt = (selected_page_number["x0"] + selected_page_number["x1"]) / 2.0
            center_drift_in = _pt_to_in(abs(center_x_pt - page_center_x_pt))
            bottom_whitespace_in = _pt_to_in(float(page.rect.height) - selected_page_number["y1"])
            low, high = policy.footer.bottom_whitespace_range_in
            if abs(center_x_pt - page_center_x_pt) > center_tolerance_pt:
                findings.append(
                    f"physical page {physical_page} (label {page_label}) has page-number center-x drift "
                    f"{center_drift_in:.4f} in above {policy.footer.center_x_tolerance_in:.4f} in"
                )
                continue
            if not (low <= bottom_whitespace_in <= high):
                findings.append(
                    f"physical page {physical_page} (label {page_label}) has footer whitespace "
                    f"{bottom_whitespace_in:.4f} in outside {low:.4f}-{high:.4f} in"
                )
                continue
            numbered_pages_checked += 1

    if findings:
        print("FAIL: dissertation exact-margin audit failed")
        print(f"- PDF: {pdf_path}")
        print(f"- Policy: {args.policy.as_posix()}")
        if policy.purpose:
            print(f"- Purpose: {policy.purpose}")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("OK: dissertation exact-margin audit passed")
    print(f"- PDF: {pdf_path}")
    print(f"- Policy: {args.policy.as_posix()}")
    if policy.purpose:
        print(f"- Purpose: {policy.purpose}")
    print(f"- Checked exact families: {checked}")
    print(f"- Checked numbered-page footers: {numbered_pages_checked}")
    for measurement in measurements:
        print(f"- {measurement}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
