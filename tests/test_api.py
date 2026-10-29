import base64
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("handler", Path(__file__).parents[1] / "app" / "handler.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class MemoryTable:
    def __init__(self):
        self.items = {}

    def put_item(self, Item, ConditionExpression):
        assert ConditionExpression == "attribute_not_exists(article_id)"
        assert Item["article_id"] not in self.items
        self.items[Item["article_id"]] = dict(Item)

    def get_item(self, Key, ConsistentRead):
        assert ConsistentRead is True
        item = self.items.get(Key["article_id"])
        return {"Item": dict(item)} if item else {}


def event(method="POST", path="/articles", body=None):
    return {"requestContext": {"http": {"method": method}}, "rawPath": path,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body if body is not None else {"title": "記事", "content": "本文"})}


class APITests(unittest.TestCase):
    def setUp(self):
        api._TABLE = MemoryTable()
        self.env = patch.dict(os.environ, {"SIMULATE_STORAGE_FAILURE": "false"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_create_then_read_preserves_japanese(self):
        result = api.handler(event(), None)
        self.assertEqual(result["statusCode"], 201)
        item = json.loads(result["body"])
        result = api.handler(event("GET", "/articles/" + item["article_id"]), None)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"]), item)

    def test_generated_ids_are_distinct(self):
        ids = [json.loads(api.handler(event(), None)["body"])["article_id"] for _ in range(2)]
        self.assertNotEqual(*ids)

    def test_missing_article(self):
        self.assertEqual(api.handler(event("GET", "/articles/" + "0" * 32), None)["statusCode"], 404)

    def test_invalid_id(self):
        self.assertEqual(api.handler(event("GET", "/articles/bad/id"), None)["statusCode"], 400)

    def test_invalid_fields_never_write(self):
        for body in [[], {}, {"title": "x"}, {"title": True, "content": "x"},
                     {"title": " ", "content": "x"}, {"title": "x" * 201, "content": "x"},
                     {"title": "x", "content": "x" * 10001},
                     {"title": "x", "content": "x", "extra": "x"}]:
            with self.subTest(body_type=type(body).__name__):
                self.assertEqual(api.handler(event(body=body), None)["statusCode"], 400)
        self.assertEqual(api._TABLE.items, {})

    def test_invalid_json(self):
        request = event()
        request["body"] = "{"
        self.assertEqual(api.handler(request, None)["statusCode"], 400)

    def test_base64_json(self):
        request = event()
        request.update(body=base64.b64encode(request["body"].encode()).decode(), isBase64Encoded=True)
        self.assertEqual(api.handler(request, None)["statusCode"], 201)

    def test_invalid_base64_and_utf8(self):
        for raw in ["%%%", base64.b64encode(b"\xff").decode()]:
            request = event()
            request.update(body=raw, isBase64Encoded=True)
            self.assertEqual(api.handler(request, None)["statusCode"], 400)

    def test_oversized_request(self):
        request = event()
        request["body"] = "x" * 50001
        self.assertEqual(api.handler(request, None)["statusCode"], 413)

    def test_content_type_required(self):
        request = event()
        request["headers"] = {}
        self.assertEqual(api.handler(request, None)["statusCode"], 415)

    def test_unknown_route(self):
        self.assertEqual(api.handler(event("DELETE", "/articles"), None)["statusCode"], 404)

    def test_failure_drill_and_recovery_keep_data(self):
        item = json.loads(api.handler(event(), None)["body"])
        get = event("GET", "/articles/" + item["article_id"])
        with patch.dict(os.environ, {"SIMULATE_STORAGE_FAILURE": "true"}):
            with self.assertLogs(api.LOGGER, level="ERROR") as captured:
                failed = api.handler(get, None)
            self.assertEqual(failed["statusCode"], 503)
            self.assertNotIn("storage_failure_drill", failed["body"])
            self.assertIn("storage_failure_drill", " ".join(captured.output))
            self.assertEqual(api.handler(event("GET", "/health"), None)["statusCode"], 200)
        self.assertEqual(json.loads(api.handler(get, None)["body"]), item)


if __name__ == "__main__":
    unittest.main()
