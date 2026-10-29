"""Synthesize real CDK constructs and verify deployment and update boundaries."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "infra/cdk"))
from content_stack import Settings, synthesize


def properties_by_type(template):
    return {resource["Type"]: resource["Properties"] for resource in template["Resources"].values()}


class CdkStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = []
        cls.manifests = []
        for settings in (Settings(), Settings(256, 14), Settings(256, 14, True)):
            with tempfile.TemporaryDirectory(prefix="cdk-test-") as directory:
                template, _ = synthesize(settings, outdir=directory)
                cls.templates.append(template)
                cls.manifests.append(json.loads((Path(directory) / "manifest.json").read_text()))

    def test_exactly_six_resources_with_the_shared_deployment_contract(self):
        self.assertEqual(len(self.templates[0]["Resources"]), 6)
        types = properties_by_type(self.templates[0])
        self.assertEqual(set(types), {"AWS::DynamoDB::Table", "AWS::Logs::LogGroup", "AWS::IAM::Role",
            "AWS::IAM::RolePolicy", "AWS::Lambda::Function", "AWS::Lambda::Url"})
        function = types["AWS::Lambda::Function"]
        self.assertEqual((function["FunctionName"], function["MemorySize"], function["Timeout"], function["Handler"], function["Runtime"]),
                         ("nilab-content-cdk", 128, 10, "index.handler", "python3.13"))
        self.assertEqual(function["Code"]["ZipFile"], (ROOT / "app/handler.py").read_text(encoding="utf-8"))
        self.assertEqual(types["AWS::Lambda::Url"]["AuthType"], "AWS_IAM")
        self.assertEqual(types["AWS::DynamoDB::Table"]["BillingMode"], "PAY_PER_REQUEST")
        self.assertEqual(types["AWS::Logs::LogGroup"]["RetentionInDays"], 7)

    def test_bounded_runtime_has_only_article_and_log_writes(self):
        types = properties_by_type(self.templates[0])
        role = types["AWS::IAM::Role"]
        self.assertEqual(role["PermissionsBoundary"], "arn:aws:iam::364561592630:policy/nilab-content-cdk-runtime-boundary")
        self.assertNotIn("ManagedPolicyArns", role)
        self.assertEqual(role["AssumeRolePolicyDocument"]["Statement"][0]["Principal"], {"Service": "lambda.amazonaws.com"})
        statements = types["AWS::IAM::RolePolicy"]["PolicyDocument"]["Statement"]
        self.assertEqual({a for s in statements for a in s["Action"]},
                         {"dynamodb:GetItem", "dynamodb:PutItem", "logs:CreateLogStream", "logs:PutLogEvents"})
        self.assertTrue(all(s["Resource"] != "*" for s in statements))

    def test_setting_update_changes_only_memory_and_log_retention(self):
        old, new = map(properties_by_type, self.templates[:2])
        changes = {(kind, key) for kind in old for key in set(old[kind]) | set(new[kind])
                   if old[kind].get(key) != new[kind].get(key)}
        self.assertEqual(changes, {("AWS::Lambda::Function", "MemorySize"), ("AWS::Logs::LogGroup", "RetentionInDays")})
        self.assertEqual(new["AWS::Lambda::Function"]["MemorySize"], 256)
        self.assertEqual(new["AWS::Logs::LogGroup"]["RetentionInDays"], 14)

    def test_drill_changes_only_the_environment_flag(self):
        before, after = self.templates[1:]
        self.assertEqual(set(before["Resources"]), set(after["Resources"]))
        old, new = map(properties_by_type, (before, after))
        for kind in old:
            if kind != "AWS::Lambda::Function":
                self.assertEqual(old[kind], new[kind])
        old_function = json.loads(json.dumps(old["AWS::Lambda::Function"]))
        old_function["Environment"]["Variables"]["SIMULATE_STORAGE_FAILURE"] = "true"
        self.assertEqual(old_function, new["AWS::Lambda::Function"])

    def test_no_published_assets_bootstrap_check_or_retained_test_data(self):
        for template, manifest in zip(self.templates, self.manifests):
            self.assertNotIn("BootstrapVersion", template.get("Parameters", {}))
            self.assertNotIn("CheckBootstrapVersion", template.get("Rules", {}))
            self.assertFalse(any(a["type"] == "cdk:asset-manifest" for a in manifest["artifacts"].values()))
            for resource in template["Resources"].values():
                if resource["Type"] in ("AWS::DynamoDB::Table", "AWS::Logs::LogGroup"):
                    self.assertEqual(resource["DeletionPolicy"], "Delete")

    def test_invalid_settings_fail_before_synthesis(self):
        for values in ((64, 7, False), (128, 2, False), (128, 7, "false"), (True, 7, False)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                Settings(*values)
