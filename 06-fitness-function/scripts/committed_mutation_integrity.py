from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from engine.control.governance.committed_mutation import assert_committed_mutation_integrity


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default=os.environ.get("SCNEHAUX_MUTATION_BASE_REF"))
    parser.add_argument("--head-ref", default="HEAD")
    args = parser.parse_args(argv)

    if not args.base_ref:
        print("[FAIL] committed mutation baseline is required via --base-ref or SCNEHAUX_MUTATION_BASE_REF")
        return 2

    try:
        report = assert_committed_mutation_integrity(
            Path.cwd(), base_ref=args.base_ref, head_ref=args.head_ref
        )
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[PASS] Committed mutation integrity")
    print(f"  base ref: {report.base_ref}")
    print(f"  merge base: {report.merge_base}")
    print(f"  head ref: {report.head_ref}")
    print(f"  governed mutations: {report.checked_mutations}")
    print("  architecture admission: unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
