from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE.parents[1]
SHA_RE = re.compile(r"[0-9a-f]{40}")


class PromotionContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((PACKAGE / "promotion.json").read_text(encoding="utf-8"))

    def test_contract_is_exact_and_pins_immutable_source(self):
        self.assertEqual(
            set(self.contract),
            {"schema_version", "repository", "authority_source_revision", "promotion", "runtime"},
        )
        self.assertEqual(self.contract["schema_version"], 1)
        self.assertEqual(self.contract["repository"], "scnehaux/codex")
        revision = self.contract["authority_source_revision"]
        self.assertIsNotNone(SHA_RE.fullmatch(revision))
        self.assertNotEqual(revision, "0" * 40)
        self.assertEqual(revision, "23b05a855419b86b61b0c9266805bb66b143c366")

    def test_promotion_is_explicit_but_not_effective_runtime_activation(self):
        self.assertEqual(
            self.contract["promotion"],
            {
                "mode": "privileged-explicit",
                "state": "source-pinned",
                "candidate_may_select_effective_revision": False,
            },
        )
        self.assertEqual(
            self.contract["runtime"],
            {
                "execution_location": "external",
                "exported_copy_required": True,
                "facts_provenance_verified": False,
                "publish_enabled": False,
                "authority_binding_advanced": False,
                "effective_enforcement_proven": False,
            },
        )

    def test_provider_binding_remains_unadvanced_until_runtime_proven(self):
        binding = (REPOSITORY_ROOT / "governance/github/authority-binding.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("authority_revision: null", binding)
        self.assertIn("promotion: privileged-explicit", binding)
        self.assertIn("state: planned", binding)
        self.assertIn("effective_enforcement_claimed: false", binding)


if __name__ == "__main__":
    unittest.main(verbosity=2)
