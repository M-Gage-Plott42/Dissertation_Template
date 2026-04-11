#!/usr/bin/env python3
"""Guard reusable rendered structural margin and footer invariants."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz


DEFAULT_POLICY = Path("refs/editorial_audit/dissertation_margin_structural_policy.yml")
POINTS_PER_INCH = 72.0


@dataclass(frozen=True)
class BodyBoxPolicy:
    left_margin_min_in: float
    right_margin_min_in: float
    tolerance_in: float


@dataclass(frozen=True)
class FooterPolicy:
    header_clear_band_in: float
    footer_band_height_in: float
    page_number_bottom_whitespace_range_in: tuple[float, float]
    page_number_center_tolerance_in: float
    suppressed_page_labels: tuple[str, ...]


@dataclass(frozen=True)
class StructuralPolicy:
    purpose: str
    body_box: BodyBoxPolicy
    footer: FooterPolicy


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split()).strip()


def _in_to_pt(value: float) -> float:
    return float(value) * POINTS_PER_INCH


def _pt_to_in(value: float) -> float:
    return float(value) / POINTS_PER_INCH


def _load_policy(path: Path) -> StructuralPolicy:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing policy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Policy file is not valid JSON/YAML-1.2 JSON subset: {exc}") from exc

    body_box_raw = raw.get("body_box", {})
    footer_raw = raw.get("footer", {})
    return StructuralPolicy(
        purpose=str(raw.get("purpose", "")),
        body_box=BodyBoxPolicy(
            left_margin_min_in=float(body_box_raw.get("left_margin_min_in", 1.0)),
            right_margin_min_in=float(body_box_raw.get("right_margin_min_in", 1.0)),
            tolerance_in=float(body_box_raw.get("tolerance_in", 0.05)),
        ),
        footer=FooterPolicy(
            header_clear_band_in=float(footer_raw.get("header_clear_band_in", 0.8)),
            footer_band_height_in=float(footer_raw.get("footer_band_height_in", 1.25)),
            page_number_bottom_whitespace_range_in=(
                float(footer_raw.get("page_number_bottom_whitespace_range_in", [0.95, 1.05])[0]),
                float(footer_raw.get("page_number_bottom_whitespace_range_in", [0.95, 1.05])[1]),
            ),
            page_number_center_tolerance_in=float(footer_raw.get("page_number_center_tolerance_in", 0.12)),
            suppressed_page_labels=tuple(
                str(item) for item in footer_raw.get("suppressed_page_labels", ["i"])
            ),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guard reusable rendered structural margin and footer invariants."
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

    left_limit_pt = _in_to_pt(policy.body_box.left_margin_min_in)
    right_limit_pt = _in_to_pt(policy.body_box.right_margin_min_in)
    margin_tolerance_pt = _in_to_pt(policy.body_box.tolerance_in)
    header_band_pt = _in_to_pt(policy.footer.header_clear_band_in)
    footer_band_start_pt = None
    center_tolerance_pt = _in_to_pt(policy.footer.page_number_center_tolerance_in)

    findings: list[str] = []
    audited_pages = 0

    try:
        pdf = fitz.open(pdf_path)
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing PDF: {pdf_path}") from exc
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise SystemExit(f"Failed to open PDF '{pdf_path}': {exc}") from exc

    with pdf:
        for page_index in range(pdf.page_count):
            page = pdf.load_page(page_index)
            physical_page = page_index + 1
            page_label = _normalize_text(str(page.get_label()))
            page_center_x_pt = float(page.rect.width) / 2.0
            footer_band_start_pt = float(page.rect.height) - _in_to_pt(policy.footer.footer_band_height_in)

            words = [
                item for item in page.get_text("words", sort=True) if _normalize_text(str(item[4]))
            ]
            normalized_words = [
                {
                    "x0": float(item[0]),
                    "y0": float(item[1]),
                    "x1": float(item[2]),
                    "y1": float(item[3]),
                    "text": _normalize_text(str(item[4])),
                }
                for item in words
            ]

            header_words = [word for word in normalized_words if word["y1"] <= header_band_pt]
            if header_words:
                findings.append(
                    f"physical page {physical_page} (label {page_label}) contains header-band text: "
                    + ", ".join(word["text"] for word in header_words[:8])
                )

            footer_words = [word for word in normalized_words if word["y0"] >= footer_band_start_pt]
            selected_page_number = None
            if page_label in policy.footer.suppressed_page_labels:
                if footer_words:
                    findings.append(
                        f"physical page {physical_page} (label {page_label}) should suppress the printed page number"
                    )
            else:
                number_candidates = [word for word in footer_words if word["text"] == page_label]
                if not number_candidates:
                    findings.append(
                        f"physical page {physical_page} (label {page_label}) is missing its footer page-number token"
                    )
                else:
                    selected_page_number = min(
                        number_candidates,
                        key=lambda word: abs(((word["x0"] + word["x1"]) / 2.0) - page_center_x_pt),
                    )
                    center_x_pt = (selected_page_number["x0"] + selected_page_number["x1"]) / 2.0
                    center_drift_in = _pt_to_in(abs(center_x_pt - page_center_x_pt))
                    bottom_whitespace_in = _pt_to_in(float(page.rect.height) - selected_page_number["y1"])
                    if abs(center_x_pt - page_center_x_pt) > center_tolerance_pt:
                        findings.append(
                            f"physical page {physical_page} (label {page_label}) has page-number center-x drift "
                            f"{center_drift_in:.4f} in above {policy.footer.page_number_center_tolerance_in:.4f} in"
                        )
                    low, high = policy.footer.page_number_bottom_whitespace_range_in
                    if not (low <= bottom_whitespace_in <= high):
                        findings.append(
                            f"physical page {physical_page} (label {page_label}) has footer whitespace "
                            f"{bottom_whitespace_in:.4f} in outside {low:.4f}-{high:.4f} in"
                        )
                    footer_extras = [
                        word
                        for word in footer_words
                        if word is not selected_page_number
                    ]
                    if footer_extras:
                        findings.append(
                            f"physical page {physical_page} (label {page_label}) has extra footer-band text: "
                            + ", ".join(word["text"] for word in footer_extras[:8])
                        )

            body_words = [
                word
                for word in normalized_words
                if word is not selected_page_number and word["y0"] < footer_band_start_pt
            ]
            if body_words:
                min_x0_pt = min(word["x0"] for word in body_words)
                max_x1_pt = max(word["x1"] for word in body_words)
                if min_x0_pt < left_limit_pt - margin_tolerance_pt:
                    findings.append(
                        f"physical page {physical_page} (label {page_label}) has left body edge "
                        f"{_pt_to_in(min_x0_pt):.4f} in below the structural 1-inch bound"
                    )
                if max_x1_pt > float(page.rect.width) - right_limit_pt + margin_tolerance_pt:
                    right_margin_in = _pt_to_in(float(page.rect.width) - max_x1_pt)
                    findings.append(
                        f"physical page {physical_page} (label {page_label}) has right body margin "
                        f"{right_margin_in:.4f} in below the structural 1-inch bound"
                    )

            audited_pages += 1

    if findings:
        print("FAIL: dissertation structural margin audit failed")
        print(f"- PDF: {pdf_path}")
        print(f"- Policy: {args.policy.as_posix()}")
        if policy.purpose:
            print(f"- Purpose: {policy.purpose}")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("OK: dissertation structural margin audit passed")
    print(f"- PDF: {pdf_path}")
    print(f"- Policy: {args.policy.as_posix()}")
    if policy.purpose:
        print(f"- Purpose: {policy.purpose}")
    print(f"- Audited pages: {audited_pages}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
