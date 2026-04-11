#!/usr/bin/env python3
"""Guard rendered preliminary-page contracts for the template dissertation PDF."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import fitz


DEFAULT_POLICY = Path("refs/editorial_audit/dissertation_prelim_contract_policy.yml")


@dataclass(frozen=True)
class DegreePolicy:
    physical_page: int
    required_degree_phrase: str


@dataclass(frozen=True)
class CopyrightPolicy:
    enabled: bool
    physical_page: int
    required_phrases: tuple[str, ...]
    center_x_tolerance: float
    center_y_range: tuple[float, float]


@dataclass(frozen=True)
class PrelimPolicy:
    purpose: str
    first_body_page_label: str
    suppressed_page_number_pages: tuple[int, ...]
    page_number_y0_range: tuple[float, float]
    page_number_y1_range: tuple[float, float]
    page_number_center_tolerance: float
    degree_page: DegreePolicy
    copyright_page: CopyrightPolicy


def _roman_lower(number: int) -> str:
    values = [
        (1000, "m"),
        (900, "cm"),
        (500, "d"),
        (400, "cd"),
        (100, "c"),
        (90, "xc"),
        (50, "l"),
        (40, "xl"),
        (10, "x"),
        (9, "ix"),
        (5, "v"),
        (4, "iv"),
        (1, "i"),
    ]
    remaining = number
    parts: list[str] = []
    for value, glyph in values:
        while remaining >= value:
            parts.append(glyph)
            remaining -= value
    return "".join(parts)


def _load_policy(path: Path) -> PrelimPolicy:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing policy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Policy file is not valid JSON/YAML-1.2 JSON subset: {exc}") from exc

    copyright_raw = raw.get("copyright_page", {})
    return PrelimPolicy(
        purpose=str(raw.get("purpose", "")),
        first_body_page_label=str(raw.get("first_body_page_label", "1")),
        suppressed_page_number_pages=tuple(
            int(item) for item in raw.get("suppressed_page_number_pages", [])
        ),
        page_number_y0_range=(
            float(raw["page_number_y0_range"][0]),
            float(raw["page_number_y0_range"][1]),
        ),
        page_number_y1_range=(
            float(raw["page_number_y1_range"][0]),
            float(raw["page_number_y1_range"][1]),
        ),
        page_number_center_tolerance=float(raw["page_number_center_tolerance"]),
        degree_page=DegreePolicy(
            physical_page=int(raw["degree_page"]["physical_page"]),
            required_degree_phrase=str(raw["degree_page"]["required_degree_phrase"]),
        ),
        copyright_page=CopyrightPolicy(
            enabled=bool(copyright_raw.get("enabled", False)),
            physical_page=int(copyright_raw.get("physical_page", 0)),
            required_phrases=tuple(str(item) for item in copyright_raw.get("required_phrases", [])),
            center_x_tolerance=float(copyright_raw.get("center_x_tolerance", 0.0)),
            center_y_range=(
                float(copyright_raw.get("center_y_range", [0.0, 0.0])[0]),
                float(copyright_raw.get("center_y_range", [0.0, 0.0])[1]),
            ),
        ),
    )


def _normalize_page_text(page: fitz.Page) -> str:
    lines = [" ".join(line.split()) for line in page.get_text("text").splitlines()]
    return " ".join(line for line in lines if line).strip()


def _bottom_band_words(page: fitz.Page) -> list[tuple[float, float, float, float, str, int, int, int]]:
    cutoff = page.rect.y1 - 120.0
    return [word for word in page.get_text("words") if word[3] > cutoff]


def _page_center(page: fitz.Page) -> tuple[float, float]:
    return page.rect.x0 + page.rect.width / 2.0, page.rect.y0 + page.rect.height / 2.0


def _content_bbox_excluding_bottom(page: fitz.Page) -> fitz.Rect | None:
    words = [word for word in page.get_text("words") if word[3] < page.rect.y1 - 120.0]
    if not words:
        return None
    x0 = min(word[0] for word in words)
    y0 = min(word[1] for word in words)
    x1 = max(word[2] for word in words)
    y1 = max(word[3] for word in words)
    return fitz.Rect(x0, y0, x1, y1)


def _first_body_physical_page(pdf: fitz.Document, first_body_label: str) -> int:
    for index in range(pdf.page_count):
        if str(pdf.load_page(index).get_label()) == first_body_label:
            return index + 1
    raise SystemExit(f"Could not find first body page label '{first_body_label}' in the PDF.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guard rendered preliminary-page contracts for the template dissertation PDF."
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

    findings: list[str] = []
    with fitz.open(pdf_path) as pdf:
        first_body_page = _first_body_physical_page(pdf, policy.first_body_page_label)
        last_prelim_page = first_body_page - 1

        for physical_page in range(1, last_prelim_page + 1):
            page = pdf.load_page(physical_page - 1)
            expected_label = _roman_lower(physical_page)
            actual_label = str(page.get_label())
            if actual_label != expected_label:
                findings.append(
                    f"physical page {physical_page} expected PDF label '{expected_label}' but found '{actual_label}'"
                )

            center_x, _ = _page_center(page)
            visible_page_number_words = [word for word in _bottom_band_words(page) if word[4] == actual_label]
            if physical_page in policy.suppressed_page_number_pages:
                if visible_page_number_words:
                    findings.append(
                        f"physical page {physical_page} prints suppressed preliminary page number '{actual_label}'"
                    )
                continue

            if not visible_page_number_words:
                findings.append(
                    f"physical page {physical_page} is missing visible preliminary page number '{actual_label}'"
                )
                continue

            page_number_word = visible_page_number_words[-1]
            y0 = float(page_number_word[1])
            y1 = float(page_number_word[3])
            center = (float(page_number_word[0]) + float(page_number_word[2])) / 2.0
            if not (policy.page_number_y0_range[0] <= y0 <= policy.page_number_y0_range[1]):
                findings.append(
                    f"physical page {physical_page} page number y0 {y0:.2f} is outside "
                    f"{policy.page_number_y0_range[0]:.2f}-{policy.page_number_y0_range[1]:.2f}"
                )
            if not (policy.page_number_y1_range[0] <= y1 <= policy.page_number_y1_range[1]):
                findings.append(
                    f"physical page {physical_page} page number y1 {y1:.2f} is outside "
                    f"{policy.page_number_y1_range[0]:.2f}-{policy.page_number_y1_range[1]:.2f}"
                )
            if abs(center - center_x) > policy.page_number_center_tolerance:
                findings.append(
                    f"physical page {physical_page} page number center x {center:.2f} "
                    f"drifts from page center {center_x:.2f} by more than {policy.page_number_center_tolerance:.2f}"
                )

        degree_page = pdf.load_page(policy.degree_page.physical_page - 1)
        degree_text = _normalize_page_text(degree_page)
        if policy.degree_page.required_degree_phrase not in degree_text:
            findings.append(
                "degree page is missing required degree phrase "
                f"'{policy.degree_page.required_degree_phrase}'"
            )

        if policy.copyright_page.enabled:
            if policy.copyright_page.physical_page > pdf.page_count:
                findings.append(
                    f"copyright page physical page {policy.copyright_page.physical_page} is missing"
                )
            else:
                page = pdf.load_page(policy.copyright_page.physical_page - 1)
                page_text = _normalize_page_text(page)
                for phrase in policy.copyright_page.required_phrases:
                    if phrase not in page_text:
                        findings.append(
                            f"copyright page is missing required phrase '{phrase}'"
                        )
                bbox = _content_bbox_excluding_bottom(page)
                if bbox is None:
                    findings.append("copyright page has no measurable content bbox")
                else:
                    center_x, center_y = _page_center(page)
                    bbox_center_x = bbox.x0 + bbox.width / 2.0
                    bbox_center_y = bbox.y0 + bbox.height / 2.0
                    if abs(bbox_center_x - center_x) > policy.copyright_page.center_x_tolerance:
                        findings.append(
                            f"copyright page content center x {bbox_center_x:.2f} drifts from page center "
                            f"{center_x:.2f} by more than {policy.copyright_page.center_x_tolerance:.2f}"
                        )
                    if not (
                        policy.copyright_page.center_y_range[0]
                        <= bbox_center_y
                        <= policy.copyright_page.center_y_range[1]
                    ):
                        findings.append(
                            f"copyright page content center y {bbox_center_y:.2f} is outside "
                            f"{policy.copyright_page.center_y_range[0]:.2f}-"
                            f"{policy.copyright_page.center_y_range[1]:.2f}"
                        )

    if findings:
        print("FAIL: dissertation preliminary-page contract audit failed")
        print(f"- PDF: {pdf_path}")
        print(f"- Policy: {args.policy.as_posix()}")
        print(f"- Purpose: {policy.purpose}")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("OK: dissertation preliminary-page contract audit passed")
    print(f"- PDF: {pdf_path}")
    print(f"- Policy: {args.policy.as_posix()}")
    print(f"- Purpose: {policy.purpose}")
    print("- Checked: roman prelim labels, suppressed printed i, bottom-centered prelim numerals, degree phrase, and configured copyright-page behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
