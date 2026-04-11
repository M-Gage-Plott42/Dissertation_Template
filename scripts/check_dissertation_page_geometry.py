#!/usr/bin/env python3
"""Guard selected rendered dissertation page-geometry sentinel surfaces."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz


DEFAULT_POLICY = Path("refs/editorial_audit/dissertation_page_geometry_policy.yml")
POINTS_PER_INCH = 72.0


@dataclass(frozen=True)
class HeadingTopCheck:
    name: str
    required_patterns: tuple[str, ...]
    phrase: str
    top_range_in: tuple[float, float]
    case_sensitive: bool


@dataclass(frozen=True)
class AppendixDividerCheck:
    name: str
    required_patterns: tuple[str, ...]
    appendix_phrase: str
    title_phrase: str
    center_x_tolerance_in: float
    center_y_range_in: tuple[float, float]
    optional: bool
    case_sensitive: bool


@dataclass(frozen=True)
class PageNumberPlacementCheck:
    name: str
    required_patterns: tuple[str, ...]
    expected_label: str
    bottom_whitespace_range_in: tuple[float, float]
    center_x_tolerance_in: float
    case_sensitive: bool


@dataclass(frozen=True)
class GeometryPolicy:
    purpose: str
    heading_top_checks: tuple[HeadingTopCheck, ...]
    appendix_divider_checks: tuple[AppendixDividerCheck, ...]
    page_number_checks: tuple[PageNumberPlacementCheck, ...]


def _normalize_line(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split()).strip()


def _page_lines(page: fitz.Page) -> list[str]:
    page_label = _normalize_line(str(page.get_label()))
    lines = [_normalize_line(line) for line in page.get_text("text", sort=True).splitlines()]
    return [line for line in lines if line and line != page_label]


def _page_text(page: fitz.Page) -> str:
    return " ".join(_page_lines(page))


def _union_rects(rects: list[fitz.Rect]) -> fitz.Rect | None:
    if not rects:
        return None
    rect = fitz.Rect(rects[0])
    for other in rects[1:]:
        rect |= other
    return rect


def _pt_to_in(value: float) -> float:
    return float(value) / POINTS_PER_INCH


def _load_policy(path: Path) -> GeometryPolicy:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing policy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Policy file is not valid JSON/YAML-1.2 JSON subset: {exc}") from exc

    heading_top_checks = tuple(
        HeadingTopCheck(
            name=str(item["name"]),
            required_patterns=tuple(str(pattern) for pattern in item.get("required_patterns", [])),
            phrase=str(item["phrase"]),
            top_range_in=(float(item["top_range_in"][0]), float(item["top_range_in"][1])),
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
            center_x_tolerance_in=float(item["center_x_tolerance_in"]),
            center_y_range_in=(float(item["center_y_range_in"][0]), float(item["center_y_range_in"][1])),
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
            bottom_whitespace_range_in=(
                float(item["bottom_whitespace_range_in"][0]),
                float(item["bottom_whitespace_range_in"][1]),
            ),
            center_x_tolerance_in=float(item["center_x_tolerance_in"]),
            case_sensitive=bool(item.get("case_sensitive", True)),
        )
        for item in raw.get("page_number_checks", [])
    )
    return GeometryPolicy(
        purpose=str(raw.get("purpose", "")),
        heading_top_checks=heading_top_checks,
        appendix_divider_checks=appendix_divider_checks,
        page_number_checks=page_number_checks,
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


def _search_rect(page: fitz.Page, phrase: str) -> fitz.Rect | None:
    return _union_rects(page.search_for(phrase))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guard selected rendered dissertation page-geometry sentinel surfaces."
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
    checked = 0

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
            checked += 1

        for check in policy.appendix_divider_checks:
            physical_page, page = _find_page(pdf, check.required_patterns, check.case_sensitive)
            if page is None or physical_page is None:
                if check.optional:
                    continue
                findings.append(f"required page family '{check.name}' was not found in the rendered PDF")
                continue
            rect = _union_rects(
                [candidate for phrase in (check.appendix_phrase, check.title_phrase) for candidate in page.search_for(phrase)]
            )
            if rect is None:
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} is missing divider text"
                )
                continue
            center_x_in = _pt_to_in((rect.x0 + rect.x1) / 2.0)
            page_center_x_in = _pt_to_in(page.rect.width / 2.0)
            center_y_in = _pt_to_in((rect.y0 + rect.y1) / 2.0)
            if abs(center_x_in - page_center_x_in) > check.center_x_tolerance_in:
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} has center-x drift "
                    f"{abs(center_x_in - page_center_x_in):.4f} in above {check.center_x_tolerance_in:.4f} in"
                )
                continue
            if not (check.center_y_range_in[0] <= center_y_in <= check.center_y_range_in[1]):
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} has center-y "
                    f"{center_y_in:.4f} in outside {check.center_y_range_in[0]:.4f}-{check.center_y_range_in[1]:.4f} in"
                )
                continue
            checked += 1

        for check in policy.page_number_checks:
            physical_page, page = _find_page(pdf, check.required_patterns, check.case_sensitive)
            if page is None or physical_page is None:
                findings.append(f"required page family '{check.name}' was not found in the rendered PDF")
                continue
            label = _normalize_line(str(page.get_label()))
            if label != check.expected_label:
                findings.append(
                    f"page family '{check.name}' landed on label '{label}', expected '{check.expected_label}'"
                )
                continue
            word_matches = [
                item for item in page.get_text("words", sort=True) if _normalize_line(str(item[4])) == check.expected_label
            ]
            if not word_matches:
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} is missing page number '{check.expected_label}'"
                )
                continue
            word = word_matches[-1]
            center_x_in = _pt_to_in((float(word[0]) + float(word[2])) / 2.0)
            page_center_x_in = _pt_to_in(page.rect.width / 2.0)
            bottom_whitespace_in = _pt_to_in(float(page.rect.height) - float(word[3]))
            if abs(center_x_in - page_center_x_in) > check.center_x_tolerance_in:
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} has page-number center-x drift "
                    f"{abs(center_x_in - page_center_x_in):.4f} in above {check.center_x_tolerance_in:.4f} in"
                )
                continue
            if not (
                check.bottom_whitespace_range_in[0]
                <= bottom_whitespace_in
                <= check.bottom_whitespace_range_in[1]
            ):
                findings.append(
                    f"page family '{check.name}' on physical page {physical_page} has bottom whitespace "
                    f"{bottom_whitespace_in:.4f} in outside "
                    f"{check.bottom_whitespace_range_in[0]:.4f}-{check.bottom_whitespace_range_in[1]:.4f} in"
                )
                continue
            checked += 1

    if findings:
        print("FAIL: dissertation page-geometry sentinel audit failed")
        print(f"- PDF: {pdf_path}")
        print(f"- Policy: {args.policy.as_posix()}")
        if policy.purpose:
            print(f"- Purpose: {policy.purpose}")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("OK: dissertation page-geometry sentinel audit passed")
    print(f"- PDF: {pdf_path}")
    print(f"- Policy: {args.policy.as_posix()}")
    if policy.purpose:
        print(f"- Purpose: {policy.purpose}")
    print(f"- Checked sentinels: {checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
