from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.control.framework.equivalence import (  # noqa: E402
    assert_framework_contract_equivalence,
)


def main() -> int:
    try:
        contract = assert_framework_contract_equivalence(ROOT)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[PASS] declarative framework contract set is strict and equivalent")
    print(f"  framework: {contract.framework_id} {contract.framework_version}")
    print(f"  families: {len(contract.families)}")
    print(f"  ownership claims: {len(contract.ownership)}")
    print(f"  canonical sha256: {contract.canonical_sha256}")
    print(f"  runtime authority: {contract.runtime_authority}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
