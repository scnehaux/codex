"""Bind release metadata or verify a declared candidate; never publishes or tags."""

from __future__ import annotations

import argparse
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

release = import_module("engine.control.governance.release")
github = import_module("engine.adapters.scm.github_release")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--authority-revision")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest-revision")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--tag")
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    try:
        if args.mode == "build":
            if not args.authority_revision or args.output is None:
                raise release.ReleaseError(
                    "build requires --authority-revision and --output"
                )
            output = args.output.resolve()
            if output.is_relative_to(root) or output.is_relative_to(
                args.authority_root.resolve()
            ):
                raise release.ReleaseError(
                    "build output must be outside both repositories"
                )
            manifest = release.build_release_manifest(
                root, args.authority_root, args.authority_revision, args.release_version
            )
            raw = release.canonical_json(manifest)
            with output.open("xb") as handle:
                handle.write(raw)
            report = {
                "status": "release_metadata_bound",
                "release_declared": False,
                "source_commit": manifest["source_commit"],
                "manifest_sha256": sha256(raw).hexdigest(),
            }
        else:
            if not args.manifest_revision or not args.manifest_sha256:
                raise release.ReleaseError(
                    "verify requires --manifest-revision and --manifest-sha256"
                )
            report = release.verify_release_manifest(
                root,
                args.authority_root,
                args.manifest_revision,
                args.release_version,
                args.manifest_sha256,
                github.verify_publication,
                tag=args.tag,
            )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
