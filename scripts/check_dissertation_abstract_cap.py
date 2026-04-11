#!/usr/bin/env python3
"""Fail when the rendered dissertation abstract exceeds UTC's word cap."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz


DEFAULT_POLICY = Path("refs/editorial_audit/dissertation_abstract_policy.yml")
WORD_RE = re.compile(r"\b[\w]+(?:[’'\-][\w]+)*\b", re.UNICODE)


@dataclass(frozen=True)
class AbstractPolicy:
    purpose: str
    start_heading: str
    stop_headings: tuple[str, ...]
    max_words: int


def _load_policy(path: Path) -> AbstractPolicy:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing policy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Policy file is not valid JSON/YAML-1.2 JSON subset: {exc}") from exc
    return AbstractPolicy(
        purpose=str(raw.get("purpose", "")),
        start_heading=str(raw.get("start_heading", "ABSTRACT")),
        stop_headings=tuple(str(item) for item in raw.get("stop_headings", [])),
        max_words=int(raw.get("max_words", 350)),
    )


def _normalize_line(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return " ".join(text.split()).strip()


def _page_lines(page: fitz.Page) -> list[str]:
    raw_text = page.get_text("text", sort=True)
    return [line for line in (_normalize_line(item) for item in raw_text.splitlines()) if line]


def _join_lines_for_reading(lines: list[str]) -> str:
    pieces: list[str] = []
    for line in lines:
        if pieces and pieces[-1].endswith("-") and line[:1].islower():
            pieces[-1] = pieces[-1][:-1] + line
        else:
            pieces.append(line)
    return " ".join(piece for piece in pieces if piece).strip()


def _extract_abstract_text(
    pdf_path: Path, policy: AbstractPolicy
) -> tuple[str, list[int], str | None]:
    seen_start = False
    extracted_pages: list[int] = []
    collected_lines: list[str] = []
    stop_heading: str | None = None

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
            page_label = _normalize_line(str(page.get_label()))
            page_lines = [line for line in _page_lines(page) if line != page_label]
            if not page_lines:
                continue

            start_at = 0
            if not seen_start:
                try:
                    start_at = page_lines.index(policy.start_heading) + 1
                except ValueError:
                    continue
                seen_start = True

            local_lines: list[str] = []
            for line in page_lines[start_at:]:
                if line in policy.stop_headings:
                    stop_heading = line
                    if local_lines:
                        extracted_pages.append(physical_page)
                    collected_lines.extend(local_lines)
                    return _join_lines_for_reading(collected_lines), extracted_pages, stop_heading
                local_lines.append(line)

            if local_lines:
                extracted_pages.append(physical_page)
            collected_lines.extend(local_lines)

    if not seen_start:
        raise SystemExit(f"Could not locate start heading '{policy.start_heading}' in the rendered PDF.")
    raise SystemExit(
        "Could not locate any configured stop heading after the abstract. "
        "Update the stop-heading policy to match the template/manuscript prelim flow."
    )


def _count_words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when the rendered dissertation abstract exceeds UTC's word cap."
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
    abstract_text, extracted_pages, stop_heading = _extract_abstract_text(pdf_path, policy)
    words = _count_words(abstract_text)

    if len(words) > policy.max_words:
        print("FAIL: dissertation abstract-cap audit failed")
        print(f"- PDF: {pdf_path}")
        print(f"- Policy: {args.policy.as_posix()}")
        if policy.purpose:
            print(f"- Purpose: {policy.purpose}")
        print("- Extracted physical pages: " + ", ".join(str(page) for page in extracted_pages))
        if stop_heading:
            print(f"- Stop heading: {stop_heading}")
        print(f"- Word count: {len(words)}")
        print(f"- UTC max words: {policy.max_words}")
        print(
            f"- Abstract contains {len(words)} words, exceeding UTC's {policy.max_words}-word dissertation cap"
        )
        return 1

    print("OK: dissertation abstract-cap audit passed")
    print(f"- PDF: {pdf_path}")
    print(f"- Policy: {args.policy.as_posix()}")
    if policy.purpose:
        print(f"- Purpose: {policy.purpose}")
    print("- Extracted physical pages: " + ", ".join(str(page) for page in extracted_pages))
    if stop_heading:
        print(f"- Stop heading: {stop_heading}")
    print(f"- Word count: {len(words)}")
    print(f"- UTC max words: {policy.max_words}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
