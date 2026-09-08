from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import re
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE.parents[1]
SHA_RE = re.compile(r"[0-9a-f]{40}")


class RuntimePromotionContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(
            (PACKAGE / "runtime-promotion.json").read_text(encoding="utf-8")
        )

    def test_contract_pins_exact_runtime_and_evaluator_sources(self):
        self.assertEqual(
            set(self.contract),
            {
                "schema_version",
                "repository",
                "runtime_source_revision",
                "runtime_source_path",
                "runtime_source_blob",
                "evaluator_source_revision",
                "evaluator_source_blob",
                "promotion",
                "runtime",
            },
        )
        self.assertEqual(self.contract["schema_version"], 1)
        self.assertEqual(self.contract["repository"], "scnehaux/codex")
        self.assertEqual(
            self.contract["runtime_source_revision"],
            "cbd64f78c8f72f28880d4673729a796b249d8eae",
        )
        self.assertEqual(
            self.contract["runtime_source_path"],
            "integrations/github-governance-evaluator/runtime.py",
        )
        self.assertEqual(
            self.contract["runtime_source_blob"],
            "c59911e9c0800c917fed21e6f33f3181c3a61e60",
        )
        self.assertEqual(
            self.contract["evaluator_source_revision"],
            "23b05a855419b86b61b0c9266805bb66b143c366",
        )
        self.assertEqual(
            self.contract["evaluator_source_blob"],
            "ab2f152c21bd6d6f22df21172c4d027035ff8c11",
        )
        for field in (
            "runtime_source_revision",
            "runtime_source_blob",
            "evaluator_source_revision",
            "evaluator_source_blob",
        ):
            self.assertIsNotNone(SHA_RE.fullmatch(self.contract[field]))
            self.assertNotEqual(self.contract[field], "0" * 40)

    def test_current_runtime_blob_is_exact_promoted_blob(self):
        path = PACKAGE / "runtime.py"
        raw = path.read_bytes()
        blob = sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
        self.assertEqual(blob, self.contract["runtime_source_blob"])

    def test_runtime_promotion_is_explicit_and_not_live_activation(self):
        self.assertEqual(
            self.contract["promotion"],
            {
                "mode": "privileged-explicit",
                "state": "runtime-source-pinned",
                "candidate_may_select_effective_revision": False,
                "auto_deploy_from_candidate": False,
            },
        )
        self.assertEqual(
            self.contract["runtime"],
            {
                "execution_location": "external",
                "exported_copy_required": True,
                "live_instance_proven": False,
                "facts_provenance_verified": False,
                "publish_enabled": False,
                "authority_binding_advanced": False,
                "effective_enforcement_proven": False,
            },
        )

    def test_runtime_pin_matches_existing_evaluator_promotion(self):
        evaluator_contract = json.loads(
            (PACKAGE / "promotion.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            self.contract["evaluator_source_revision"],
            evaluator_contract["authority_source_revision"],
        )

    def test_provider_binding_remains_unadvanced_until_live_runtime_proof(self):
        binding = (
            REPOSITORY_ROOT / "governance/github/authority-binding.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("authority_revision: null", binding)
        self.assertIn("candidate_revision_as_authority: false", binding)
        self.assertIn("auto_deploy_from_candidate: false", binding)
        self.assertIn("promotion: privileged-explicit", binding)
        self.assertIn("state: planned", binding)
        self.assertIn("effective_enforcement_claimed: false", binding)


if __name__ == "__main__":
    unittest.main(verbosity=2)
