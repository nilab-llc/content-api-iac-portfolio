"""Explicit live verification: creates one article. Never called by CI."""
import argparse
import hashlib
import json
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--allow-create-test-article", action="store_true", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"https://[a-z0-9]+\.lambda-url\.ap-northeast-1\.on\.aws/?", args.url):
        parser.error("Use the deployed Tokyo Function URL, without query parameters.")
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    session = boto3.Session(profile_name=args.profile, region_name="ap-northeast-1")
    credentials = session.get_credentials().get_frozen_credentials()
    base = args.url.rstrip("/")

    def send(method, path, payload=None, signed=True):
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        headers = {"Content-Type": "application/json",
                   "X-Amz-Content-SHA256": hashlib.sha256(body or b"").hexdigest()}
        if signed:
            request = AWSRequest(method=method, url=base + path, data=body, headers=headers)
            SigV4Auth(credentials, "lambda", "ap-northeast-1").add_auth(request)
            headers = dict(request.headers)
        request = Request(base + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=20) as reply:
                return reply.status, json.loads(reply.read())
        except HTTPError as error:
            return error.code, None

    status, _ = send("GET", "/health", signed=False)
    if status != 403:
        raise RuntimeError(f"Unauthenticated request: expected 403, got {status}")
    status, _ = send("GET", "/health")
    if status != 200:
        raise RuntimeError(f"Authenticated health: expected 200, got {status}")
    status, item = send("POST", "/articles", {"title": "IaC verification", "content": "共通動作確認"})
    if status != 201:
        raise RuntimeError(f"Create: expected 201, got {status}")
    status, fetched = send("GET", "/articles/" + item["article_id"])
    if status != 200 or fetched != item:
        raise RuntimeError(f"Read-back mismatch, status={status}")
    print(json.dumps({"result": "PASS", "unsigned_status": 403,
                      "article_id": item["article_id"], "read_status": status}, ensure_ascii=False))


if __name__ == "__main__":
    main()
