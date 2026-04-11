#!/usr/bin/env python3
"""Fail when the rendered dissertation PDF contains live links or annotations."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import fitz


DEFAULT_POLICY = Path("refs/editorial_audit/dissertation_hyperlink_policy.yml")

KIND_NAMES = {
    getattr(fitz, "LINK_NONE", 0): "LINK_NONE",
    getattr(fitz, "LINK_GOTO", 1): "LINK_GOTO",
    getattr(fitz, "LINK_URI", 2): "LINK_URI",
    getattr(fitz, "LINK_LAUNCH", 3): "LINK_LAUNCH",
    getattr(fitz, "LINK_NAMED", 4): "LINK_NAMED",
    getattr(fitz, "LINK_GOTOR", 5): "LINK_GOTOR",
}


@dataclass(frozen=True)
class LinkFinding:
    page: int
    page_label: str
    kind: str
    detail: str


def _load_policy(path: Path) -> tuple[str, bool]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing policy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Policy file is not valid JSON/YAML-1.2 JSON subset: {exc}") from exc
    return str(raw.get("purpose", "")), bool(raw.get("allow_any_links", False))


def _inspect_pdf(pdf_path: Path, allow_any_links: bool) -> list[LinkFinding]:
    findings: list[LinkFinding] = []
    with fitz.open(pdf_path) as pdf:
        for page_index in range(pdf.page_count):
            page = pdf.load_page(page_index)
            page_no = page_index + 1
            page_label = str(page.get_label())
            for link in page.get_links():
                kind_value = int(link.get("kind", 0))
                kind_name = KIND_NAMES.get(kind_value, f"LINK_{kind_value}")
                detail_bits: list[str] = []
                if link.get("uri"):
                    detail_bits.append(f"uri={link['uri']}")
                if link.get("page") is not None:
                    detail_bits.append(f"dest_page={int(link['page']) + 1}")
                if link.get("to"):
                    detail_bits.append(f"dest_point={link['to']}")
                if not allow_any_links:
                    findings.append(
                        LinkFinding(
                            page=page_no,
                            page_label=page_label,
                            kind=kind_name,
                            detail=", ".join(detail_bits) or "active PDF link present",
                        )
                    )
            for annot in list(page.annots() or []):
                annot_type = annot.type[1] if isinstance(annot.type, tuple) else str(annot.type)
                info = annot.info or {}
                detail = info.get("content") or info.get("title") or "annotation present"
                if not allow_any_links:
                    findings.append(
                        LinkFinding(
                            page=page_no,
                            page_label=page_label,
                            kind=f"ANNOT_{annot_type}",
                            detail=detail,
                        )
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when the rendered dissertation PDF contains live links or annotations."
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
    purpose, allow_any_links = _load_policy(policy_path)
    findings = _inspect_pdf(pdf_path, allow_any_links=allow_any_links)

    if findings:
        print("FAIL: dissertation hyperlink audit failed")
        print(f"- PDF: {pdf_path}")
        print(f"- Policy: {args.policy.as_posix()}")
        if purpose:
            print(f"- Purpose: {purpose}")
        for finding in findings:
            print(
                f"- Physical page {finding.page} (label {finding.page_label}): "
                f"{finding.kind} -> {finding.detail}"
            )
        return 1

    print("OK: dissertation hyperlink audit passed")
    print(f"- PDF: {pdf_path}")
    print(f"- Policy: {args.policy.as_posix()}")
    if purpose:
        print(f"- Purpose: {purpose}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
