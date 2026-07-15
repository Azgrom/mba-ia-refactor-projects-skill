#!/usr/bin/env python3
"""Verify that distributed refactor-arch skill trees are byte-equivalent."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import NamedTuple


class DistributionResult(NamedTuple):
    equivalent: bool
    errors: tuple[str, ...]


def _included_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        files[relative.as_posix()] = path
    return files


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_distribution(
    canonical: Path, copies: list[Path]
) -> DistributionResult:
    """Compare relative file sets and content digests for every copy."""

    canonical = Path(canonical)
    copies = [Path(copy) for copy in copies]
    errors: list[str] = []

    if not canonical.is_dir():
        return DistributionResult(
            False, (f"Canonical skill directory does not exist: {canonical}",)
        )
    canonical_files = _included_files(canonical)

    for copy in copies:
        if not copy.is_dir():
            errors.append(f"Skill copy directory does not exist: {copy}")
            continue
        copy_files = _included_files(copy)
        canonical_names = set(canonical_files)
        copy_names = set(copy_files)

        missing = sorted(canonical_names - copy_names)
        if missing:
            errors.append(f"{copy}: missing path {missing[0]}")
            continue
        extra = sorted(copy_names - canonical_names)
        if extra:
            errors.append(f"{copy}: extra path {extra[0]}")
            continue

        for relative_path in sorted(canonical_names):
            expected = _sha256(canonical_files[relative_path])
            actual = _sha256(copy_files[relative_path])
            if expected != actual:
                errors.append(
                    f"{copy}: digest mismatch for {relative_path}; expected {expected}, actual {actual}"
                )
                break

    return DistributionResult(not errors, tuple(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canonical", type=Path)
    parser.add_argument("copies", nargs="+", type=Path)
    args = parser.parse_args()

    result = verify_distribution(args.canonical, args.copies)
    if result.equivalent:
        print(f"EQUIVALENT: {args.canonical} == {len(args.copies)} copies")
        return 0
    for error in result.errors:
        print(f"ERROR: {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
