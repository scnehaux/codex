from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.control.governance.dependency_update import (  # noqa: E402
    assert_dependency_update_integrity,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-ref",
        default=os.environ.get("SCNEHAUX_MUTATION_BASE_REF"),
    )
    parser.add_argument("--head-ref", default="HEAD")
    args = parser.parse_args(argv)

    if not args.base_ref:
        print("[FAIL] dependency-update baseline is required")
        return 2

    try:
        report = assert_dependency_update_integrity(
            Path.cwd(),
            base_ref=args.base_ref,
            head_ref=args.head_ref,
        )
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[PASS] dependency update integrity")
    print(f"  changed files: {len(report.changed_files)}")
    bundles = ", ".join(report.checked_bundles) if report.checked_bundles else "none"
    print(f"  checked bundles: {bundles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
