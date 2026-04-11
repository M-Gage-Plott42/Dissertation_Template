#!/usr/bin/env python3
"""Guard rendered TOC sentinel entries against live body-page labels."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz


DEFAULT_POLICY = Path("refs/editorial_audit/dissertation_toc_contract_policy.yml")
DOT_LEADER_RE = re.compile(r"\.{2,}")


@dataclass(frozen=True)
class TocSectionPolicy:
    start_heading: str
    stop_page_headings: tuple[str, ...]


@dataclass(frozen=True)
class TocSentinel:
    name: str
    toc_text: str
    body_patterns: tuple[str, ...]
    optional: bool
    case_sensitive: bool


@dataclass(frozen=True)
class TocPolicy:
    purpose: str
    toc_section: TocSectionPolicy
    entries: tuple[TocSentinel, ...]


def _normalize_line(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split()).strip()


def _load_policy(path: Path) -> TocPolicy:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing policy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Policy file is not valid JSON/YAML-1.2 JSON subset: {exc}") from exc

    toc_section_raw = raw.get("toc_section", {})
    toc_section = TocSectionPolicy(
        start_heading=str(toc_section_raw.get("start_heading", "TABLE OF CONTENTS")),
        stop_page_headings=tuple(str(item) for item in toc_section_raw.get("stop_page_headings", [])),
    )
    entries = tuple(
        TocSentinel(
            name=str(item["name"]),
            toc_text=str(item["toc_text"]),
            body_patterns=tuple(str(pattern) for pattern in item.get("body_patterns", [])),
            optional=bool(item.get("optional", False)),
            case_sensitive=bool(item.get("case_sensitive", True)),
        )
        for item in raw.get("entries", [])
    )
    return TocPolicy(
        purpose=str(raw.get("purpose", "")),
        toc_section=toc_section,
        entries=entries,
    )


def _page_lines(page: fitz.Page) -> list[str]:
    page_label = _normalize_line(str(page.get_label()))
    lines = [_normalize_line(line) for line in page.get_text("text", sort=True).splitlines()]
    return [line for line in lines if line and line != page_label]


def _normalize_search_text(lines: list[str]) -> str:
    text = " ".join(lines)
    text = DOT_LEADER_RE.sub(" ", text)
    return _normalize_line(text)


def _collect_toc_text(pdf: fitz.Document, policy: TocSectionPolicy) -> tuple[str, list[int]]:
    collecting = False
    toc_pages: list[int] = []
    toc_lines: list[str] = []

    for page_index in range(pdf.page_count):
        page = pdf.load_page(page_index)
        physical_page = page_index + 1
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

        toc_pages.append(physical_page)
        toc_lines.extend(lines)

    if not toc_pages:
        raise SystemExit(
            f"Could not locate TOC start heading '{policy.start_heading}' in the rendered PDF."
        )
    return _normalize_search_text(toc_lines), toc_pages


def _find_body_page(pdf: fitz.Document, entry: TocSentinel) -> tuple[int | None, str | None]:
    flags = 0 if entry.case_sensitive else re.IGNORECASE
    for page_index in range(pdf.page_count):
        page = pdf.load_page(page_index)
        page_text = _normalize_search_text(_page_lines(page))
        if all(re.search(pattern, page_text, flags) for pattern in entry.body_patterns):
            physical_page = page_index + 1
            return physical_page, _normalize_line(str(page.get_label()))
    return None, None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guard rendered dissertation TOC sentinel entries against live body-page labels."
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
    checked_entries = 0

    with pdf:
        toc_text, toc_pages = _collect_toc_text(pdf, policy.toc_section)
        for entry in policy.entries:
            body_page, body_label = _find_body_page(pdf, entry)
            toc_pattern = re.escape(_normalize_line(entry.toc_text))

            if body_page is None or body_label is None:
                if entry.optional:
                    if re.search(toc_pattern, toc_text) is not None:
                        findings.append(
                            f"optional sentinel '{entry.name}' appears in the TOC but its body page was not found"
                        )
                    continue
                findings.append(f"required sentinel '{entry.name}' body page was not found in the rendered PDF")
                continue

            checked_entries += 1
            entry_pattern = rf"{toc_pattern}\s+{re.escape(body_label)}"
            flags = 0 if entry.case_sensitive else re.IGNORECASE
            if re.search(entry_pattern, toc_text, flags) is None:
                findings.append(
                    f"TOC is missing sentinel '{entry.name}' with live page label '{body_label}'"
                )

    if findings:
        print("FAIL: dissertation TOC sentinel audit failed")
        print(f"- PDF: {pdf_path}")
        print(f"- Policy: {args.policy.as_posix()}")
        if policy.purpose:
            print(f"- Purpose: {policy.purpose}")
        print("- TOC physical pages: " + ", ".join(str(page) for page in toc_pages))
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("OK: dissertation TOC sentinel audit passed")
    print(f"- PDF: {pdf_path}")
    print(f"- Policy: {args.policy.as_posix()}")
    if policy.purpose:
        print(f"- Purpose: {policy.purpose}")
    print("- TOC physical pages: " + ", ".join(str(page) for page in toc_pages))
    print(f"- Checked sentinels: {checked_entries}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
