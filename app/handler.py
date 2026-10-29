"""Shared application for Terraform, CloudFormation and CDK deployments."""
import base64
import binascii
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
_TABLE = None
ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def table():
    global _TABLE
    if os.environ.get("SIMULATE_STORAGE_FAILURE", "false") == "true":
        raise RuntimeError("storage_failure_drill")
    if _TABLE is None:
        import boto3
        _TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _TABLE


def response(status, payload):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(payload, ensure_ascii=False),
    }


def handler(event, context):
    request_id = getattr(context, "aws_request_id", "local")
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")
    try:
        if path == "/health" and method == "GET":
            # Liveness only: this route does not check DynamoDB availability.
            result = response(200, {"status": "ok"})
        elif path == "/articles" and method == "POST":
            headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
            if headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
                result = response(415, {"error": "application_json_required"})
            else:
                result = create_article(event)
        elif path.startswith("/articles/") and method == "GET":
            article_id = path[len("/articles/"):]
            if not ID_PATTERN.fullmatch(article_id):
                result = response(400, {"error": "invalid_article_id"})
            else:
                item = table().get_item(Key={"article_id": article_id}, ConsistentRead=True).get("Item")
                result = response(200, item) if item else response(404, {"error": "not_found"})
        else:
            result = response(404, {"error": "route_not_found"})
    except Exception:
        # Stack traces are logged; credentials and article bodies are never logged.
        LOGGER.exception("storage_or_application_error request_id=%s", request_id)
        result = response(503, {"error": "service_unavailable", "request_id": request_id})
    LOGGER.info(json.dumps({"request_id": request_id, "method": method,
                            "status": result["statusCode"]}))
    return result


def create_article(event):
    raw = event.get("body") or ""
    try:
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw, validate=True).decode("utf-8")
        if len(raw.encode("utf-8")) > 50000:
            return response(413, {"error": "body_too_large"})
        payload = json.loads(raw)
    except (ValueError, UnicodeError, binascii.Error):
        return response(400, {"error": "invalid_json"})
    if not isinstance(payload, dict) or set(payload) != {"title", "content"}:
        return response(400, {"error": "title_and_content_required"})
    title, content = payload["title"], payload["content"]
    if (not isinstance(title, str) or not 1 <= len(title.strip()) <= 200
            or not isinstance(content, str) or not 1 <= len(content.strip()) <= 10000):
        return response(400, {"error": "invalid_title_or_content"})
    item = {"article_id": uuid.uuid4().hex, "title": title.strip(), "content": content,
            "created_at": datetime.now(timezone.utc).isoformat()}
    table().put_item(Item=item, ConditionExpression="attribute_not_exists(article_id)")
    return response(201, item)
