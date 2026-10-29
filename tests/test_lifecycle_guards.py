"""Reject mixed-target records before obtaining any AWS session."""
import json
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


class LifecycleGuards(unittest.TestCase):
    def run_guard(self, filename, record, message, target="cloudformation"):
        script = Path(__file__).resolve().parents[1] / "scripts/verify_lifecycle.py"
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / filename).write_text(json.dumps(record), encoding="utf-8")
            session = Mock(side_effect=AssertionError("AWS session must not be opened"))
            with patch.dict(sys.modules, {"boto3": types.SimpleNamespace(Session=session)}), patch.object(
                sys, "argv", [str(script), "backup", "--target", target, "--records", directory]
            ):
                with self.assertRaisesRegex(RuntimeError, message):
                    runpy.run_path(str(script), run_name="__main__")
                session.assert_not_called()

    def test_existing_phase_is_not_overwritten(self):
        self.run_guard("backup.json", {"target": "cloudformation"}, "already exists")

    def test_terraform_records_cannot_be_used_for_cloudformation(self):
        self.run_guard("preserved.json", {"target": "terraform"}, "different IaC target")

    def test_legacy_records_are_treated_as_terraform(self):
        self.run_guard("preserved.json", {"phase": "preserved"}, "different IaC target")

    def test_cloudformation_records_cannot_be_used_for_cdk(self):
        self.run_guard("preserved.json", {"target": "cloudformation"}, "different IaC target", target="cdk")

    def test_cdk_records_cannot_be_used_for_cloudformation(self):
        self.run_guard("preserved.json", {"target": "cdk"}, "different IaC target")
