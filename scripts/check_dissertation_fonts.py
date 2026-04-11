#!/usr/bin/env python3
"""Validate rendered dissertation font compliance from pdffonts output."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_POLICY = Path("refs/editorial_audit/dissertation_font_policy.yml")


@dataclass(frozen=True)
class FontPolicy:
    purpose: str
    approved_body_prefixes: tuple[str, ...]
    allowed_aux_prefixes: tuple[str, ...]
    disallowed_text_tokens: tuple[str, ...]


@dataclass(frozen=True)
class FontRecord:
    name: str
    embedded: bool
    subset: bool
    unicode: bool


def _load_policy(path: Path) -> FontPolicy:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing policy file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Policy file is not valid JSON/YAML-1.2 JSON subset: {exc}") from exc
    return FontPolicy(
        purpose=str(raw.get("purpose", "")),
        approved_body_prefixes=tuple(str(item) for item in raw.get("approved_body_prefixes", [])),
        allowed_aux_prefixes=tuple(str(item) for item in raw.get("allowed_aux_prefixes", [])),
        disallowed_text_tokens=tuple(str(item) for item in raw.get("disallowed_text_tokens", [])),
    )


def _run_text(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"required tool '{cmd[0]}' is not available on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "command failed"
        raise RuntimeError(f"{' '.join(cmd)} :: {detail}") from exc
    return proc.stdout


def _parse_pdffonts(text: str) -> list[FontRecord]:
    records: list[FontRecord] = []
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        raise RuntimeError("unexpected pdffonts output; expected header plus font rows")

    for line in lines[2:]:
        parts = line.split()
        if len(parts) < 8:
            raise RuntimeError(f"could not parse pdffonts row: {line}")
        records.append(
            FontRecord(
                name=parts[0],
                embedded=(parts[-5] == "yes"),
                subset=(parts[-4] == "yes"),
                unicode=(parts[-3] == "yes"),
            )
        )
    return records


def _strip_subset_prefix(name: str) -> str:
    return re.sub(r"^[A-Z]{6}\+", "", name)


def _is_approved_body(name: str, policy: FontPolicy) -> bool:
    return any(name.startswith(prefix) for prefix in policy.approved_body_prefixes)


def _is_allowed_aux(name: str, policy: FontPolicy) -> bool:
    return any(name.startswith(prefix) for prefix in policy.allowed_aux_prefixes)


def _has_disallowed_text_token(name: str, policy: FontPolicy) -> bool:
    return any(token in name for token in policy.disallowed_text_tokens)


def validate(pdf_path: Path, policy: FontPolicy) -> tuple[list[str], list[str]]:
    tool = shutil.which("pdffonts")
    if tool is None:
        return ["missing dependency 'pdffonts' (install poppler)"], []
    if not pdf_path.exists():
        return [f"missing PDF: {pdf_path}"], []

    try:
        output = _run_text([tool, str(pdf_path)])
        records = _parse_pdffonts(output)
    except RuntimeError as exc:
        return [str(exc)], []

    normalized = sorted({_strip_subset_prefix(record.name) for record in records})
    issues: list[str] = []

    if not any(_is_approved_body(name, policy) for name in normalized):
        issues.append(
            "missing approved body font family; expected at least one of: "
            + ", ".join(policy.approved_body_prefixes)
        )

    unembedded = sorted({_strip_subset_prefix(r.name) for r in records if not r.embedded})
    if unembedded:
        issues.append("non-embedded fonts present: " + ", ".join(unembedded))

    disallowed = sorted(name for name in normalized if _has_disallowed_text_token(name, policy))
    if disallowed:
        issues.append("disallowed text-font families present: " + ", ".join(disallowed))

    recognized = {
        name
        for name in normalized
        if _is_approved_body(name, policy)
        or _is_allowed_aux(name, policy)
        or _has_disallowed_text_token(name, policy)
    }
    unknown = sorted(set(normalized).difference(recognized))
    if issues and unknown:
        issues.append("unclassified font families also present: " + ", ".join(unknown))

    return issues, normalized


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when the rendered dissertation PDF lacks an approved body font "
            "family or includes obvious noncompliant body-text families."
        )
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
    issues, fonts = validate(pdf_path, policy)

    if issues:
        print("FAIL: dissertation font compliance check failed")
        print(f"- PDF: {pdf_path}")
        print(f"- Policy: {args.policy.as_posix()}")
        if policy.purpose:
            print(f"- Purpose: {policy.purpose}")
        if fonts:
            print("- Fonts detected: " + ", ".join(fonts))
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("OK: dissertation font compliance check passed")
    print(f"- PDF: {pdf_path}")
    print(f"- Policy: {args.policy.as_posix()}")
    if policy.purpose:
        print(f"- Purpose: {policy.purpose}")
    if fonts:
        print("- Fonts detected: " + ", ".join(fonts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
