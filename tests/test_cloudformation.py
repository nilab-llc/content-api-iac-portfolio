"""Run the shared API behavior suite against the actual inline deployment source."""
import json
from pathlib import Path
import types
from unittest.mock import patch

import test_api


class InlineAPITests(test_api.APITests):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "infra/cloudformation/template.json"
        source = json.loads(path.read_text(encoding="utf-8"))["Resources"]["ApiFunction"]["Properties"]["Code"]["ZipFile"]
        inline = types.ModuleType("index")
        exec(compile(source, "index.py", "exec"), inline.__dict__)
        self.replace = patch.object(test_api, "api", inline)
        self.replace.start()
        self.addCleanup(self.replace.stop)
        super().setUp()
