"""Verify consolidation preserves the exact action/resource/condition combinations."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_cdk_permissions import atoms, proposals


class CdkPermissionTests(unittest.TestCase):
    def test_scope_is_exactly_existing_permissions_plus_cdk(self):
        result = proposals()
        existing = json.loads((ROOT / "permissions/cloudformation/sso-inline-merged-proposal.json").read_text())
        self.assertEqual(atoms(result["sso-inline-merged-proposal.json"]),
                         atoms(existing) | atoms(result["deploy-and-verify-additions.json"]))

    def test_scoped_boundary_condition_cannot_cross_between_runtime_roles(self):
        merged = proposals()["sso-inline-merged-proposal.json"]
        for effect, action, resource, condition in atoms(merged):
            if action == "iam:CreateRole":
                self.assertEqual(effect, "Allow")
                boundary = json.loads(condition)["ArnEquals"]["iam:PermissionsBoundary"]
                self.assertEqual(boundary, resource.replace(":role/", ":policy/") + "-boundary")
        self.assertLessEqual(len(json.dumps(merged, separators=(",", ":"))), 10240)
