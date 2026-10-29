"""Exercise the actual CDK-exported Python source with the shared behavior suite."""
import json
from pathlib import Path
import types
from unittest.mock import patch

import test_api


class CdkInlineAPITests(test_api.APITests):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        template = json.loads((root / "infra/cdk/template.json").read_text(encoding="utf-8"))
        functions = [r for r in template["Resources"].values() if r["Type"] == "AWS::Lambda::Function"]
        source = functions[0]["Properties"]["Code"]["ZipFile"]
        inline = types.ModuleType("index")
        exec(compile(source, "index.py", "exec"), inline.__dict__)
        self.replace = patch.object(test_api, "api", inline)
        self.replace.start()
        self.addCleanup(self.replace.stop)
        super().setUp()
