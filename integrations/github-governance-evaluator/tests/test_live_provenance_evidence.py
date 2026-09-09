from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
EVALUATOR_DIR = ROOT / "integrations/github-governance-evaluator"
EVIDENCE = ROOT / "governance/github/evidence/live-provenance-001.json"
BINDING = ROOT / "governance/github/authority-binding.yaml"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


class LiveProvenanceEvidenceTests(unittest.TestCase):
    def test_evidence_is_bound_to_promoted_source_and_exact_live_result(self):
        evidence = _json(EVIDENCE)
        runtime = _json(EVALUATOR_DIR / "runtime-promotion.json")
        evaluator = _json(EVALUATOR_DIR / "promotion.json")

        self.assertEqual(evidence["contract_version"], 1)
        self.assertEqual(
            evidence["kind"], "scm-external-authority-live-provenance-evidence"
        )
        self.assertEqual(evidence["provider"], "github")
        self.assertEqual(evidence["repository"], "scnehaux/codex")
        self.assertEqual(evidence["evidence_id"], "live-provenance-001")
        self.assertEqual(
            evidence["source"],
            {
                "runtime_source_revision": runtime["runtime_source_revision"],
                "runtime_source_path": runtime["runtime_source_path"],
                "runtime_source_blob": runtime["runtime_source_blob"],
                "evaluator_source_revision": runtime["evaluator_source_revision"],
                "evaluator_source_blob": runtime["evaluator_source_blob"],
            },
        )
        self.assertEqual(
            runtime["evaluator_source_revision"], evaluator["authority_source_revision"]
        )
        self.assertEqual(
            _git_blob(EVALUATOR_DIR / "runtime.py"), runtime["runtime_source_blob"]
        )
        self.assertEqual(
            _git_blob(EVALUATOR_DIR / "evaluator.py"), runtime["evaluator_source_blob"]
        )

        self.assertEqual(
            evidence["execution"],
            {
                "location": "external",
                "exported_copy_required": True,
                "raw_blob_verification": {
                    "mode": "git-object-raw-bytes",
                    "runtime_verified": True,
                    "evaluator_verified": True,
                },
                "candidate_code_executed": False,
                "credentials_used": False,
            },
        )
        observation = evidence["observation"]
        self.assertEqual(observation["runtime_result_status"], "runtime_evaluation_complete")
        self.assertEqual(observation["pull_request"], 15)
        self.assertEqual(observation["pull_state"], "open")
        self.assertEqual(
            observation["base_sha"], "ed893641a9c96a6cb4c8a590f2757e32116721f6"
        )
        self.assertEqual(
            observation["head_sha"], "968e496ff6de16b223bd9a15122ee81ed4ee1e5a"
        )
        self.assertEqual(observation["changed_files"], [".gitignore"])
        self.assertIs(observation["facts_collected_independently"], True)
        self.assertEqual(observation["governance_decision"], "pass")
        self.assertEqual(observation["runtime_failure_reasons"], [])
        self.assertEqual(observation["runtime_only_protected_mutations"], [])

        qualification = observation["candidate_qualification"]
        self.assertEqual(qualification["context"], "Governance Qualification")
        self.assertEqual(qualification["result"], "pass")
        self.assertEqual(qualification["check_run_id"], 102414770301)
        self.assertEqual(qualification["head_sha"], observation["head_sha"])
        self.assertEqual(qualification["source"], "github-checks-api")
        self.assertEqual(qualification["source_app_id"], 15368)
        self.assertEqual(qualification["source_app_slug"], "github-actions")
        self.assertIs(qualification["source_verified"], True)
        self.assertEqual(qualification["status"], "completed")
        self.assertEqual(qualification["conclusion"], "success")

    def test_attestation_advances_only_live_proof_not_publisher_or_enforcement(self):
        evidence = _json(EVIDENCE)
        self.assertEqual(
            evidence["attestation"],
            {
                "live_instance_proven": True,
                "facts_provenance_evidenced": True,
                "publisher_proven": False,
                "authority_binding_advanced": False,
                "effective_enforcement_proven": False,
            },
        )
        self.assertEqual(
            evidence["source_runtime_self_report"],
            {
                "runtime_source_promoted": False,
                "facts_provenance_verified": False,
                "publish_enabled": False,
                "authority_binding_advanced": False,
                "effective_enforcement_proven": False,
            },
        )

        binding = BINDING.read_text(encoding="utf-8")
        required = (
            "authority_revision: null",
            "state: planned",
            "live_provenance_evidence: governance/github/evidence/live-provenance-001.json",
            "publisher_evidence: null",
            "effective_enforcement_claimed: false",
        )
        for item in required:
            self.assertIn(item, binding)


if __name__ == "__main__":
    unittest.main()
