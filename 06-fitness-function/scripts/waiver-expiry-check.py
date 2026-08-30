import os
from datetime import date
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from engine.control.parsing.markdown_ast import parse_date, parse_frontmatter


def default_adr_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "..", "05-decisions")


def check_waiver_expiry(
    adr_dir: str | None = None,
    current_date: date | None = None,
) -> int:
    """
    Scan accepted ADR exceptions for expiration.

    Returns 1 for expired waivers or invalid expiry dates, otherwise 0.
    """
    adr_dir = adr_dir or default_adr_dir()
    today = current_date or date.today()
    has_errors = False
    warning_days = 30

    print("Checking active waiver ADRs for expiration...")

    for root, _, files in os.walk(adr_dir):
        for file in files:
            if not file.endswith(".md") or file.upper() == "INDEX.md":
                continue

            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as handle:
                content = handle.read()

            doc_meta, _ = parse_frontmatter(content)
            if not doc_meta:
                continue

            if (
                doc_meta.get("adr_type") != "exception"
                or doc_meta.get("status") != "accepted"
            ):
                continue

            exception_info = doc_meta.get("exception_info", {})
            expiry_date_raw = exception_info.get("expiry_date")
            if not expiry_date_raw:
                continue

            expiry_date = parse_date(expiry_date_raw)
            if not expiry_date:
                print(
                    f"[ERROR] Invalid expiry_date format in {file}: "
                    f"{expiry_date_raw}"
                )
                has_errors = True
                continue

            delta = (expiry_date - today).days
            rel_path = os.path.relpath(file_path, adr_dir).replace("\\", "/")

            if delta < 0:
                print(
                    f"[CRITICAL] Expired waiver: {rel_path} expired on "
                    f"{expiry_date} ({abs(delta)} days ago)"
                )
                has_errors = True
            elif delta <= warning_days:
                print(
                    f"[WARNING] Expiring soon: {rel_path} expires in "
                    f"{delta} days on {expiry_date}"
                )

    if has_errors:
        print("\n[FAIL] Expiry check failed due to expired waivers.")
        return 1

    print("\n[PASS] No expired waivers found.")
    return 0


def main() -> int:
    return check_waiver_expiry()


if __name__ == "__main__":
    raise SystemExit(main())
