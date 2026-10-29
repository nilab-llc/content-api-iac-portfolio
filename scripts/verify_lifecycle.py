"""Explicit operational checks for the deployed portfolio. Never run in CI."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["backup", "preserved", "failure", "logs", "restored", "rebuild"])
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--target", choices=["terraform", "cloudformation", "cdk"], default="terraform")
    args = parser.parse_args()
    name = {"terraform": "nilab-content-tf", "cloudformation": "nilab-content-cfn", "cdk": "nilab-content-cdk"}[args.target]
    recordfile = args.records / (args.phase + ".json")
    if recordfile.exists():
        raise RuntimeError("Phase record already exists; refusing to overwrite it")
    for existing in args.records.glob("*.json"):
        if existing.name == "articles-before.json":
            continue
        record = json.loads(existing.read_text(encoding="utf-8"))
        if record.get("target", "terraform") != args.target:
            raise RuntimeError("Records belong to a different IaC target")
    import boto3
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    session = boto3.Session(profile_name="nilab-readonly", region_name="ap-northeast-1")
    identity = session.client("sts").get_caller_identity()
    if identity["Account"] != "364561592630":
        raise RuntimeError("Unexpected AWS account")
    config = session.client("lambda").get_function_url_config(FunctionName=name)
    assert config["AuthType"] == "AWS_IAM"
    base = config["FunctionUrl"].rstrip("/")
    credentials = session.get_credentials().get_frozen_credentials()
    args.records.mkdir(parents=True, exist_ok=True)
    datafile = args.records / "articles-before.json"
    state = Path(__file__).resolve().parents[1] / "infra/terraform/terraform.tfstate"

    def send(method, path, payload=None, signed=True):
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        headers = {"Content-Type": "application/json",
                   "X-Amz-Content-SHA256": hashlib.sha256(body or b"").hexdigest()}
        if signed:
            request = AWSRequest(method=method, url=base + path, data=body, headers=headers)
            SigV4Auth(credentials, "lambda", "ap-northeast-1").add_auth(request)
            headers = dict(request.headers)
        try:
            with urlopen(Request(base + path, data=body, headers=headers, method=method), timeout=20) as reply:
                return reply.status, json.loads(reply.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    result = {"target": args.target, "resource_name": name, "phase": args.phase, "time_utc": datetime.now(timezone.utc).isoformat()}
    if args.phase == "backup":
        table = session.resource("dynamodb").Table(name)
        items = []
        page = table.scan(ConsistentRead=True)
        items.extend(page.get("Items", []))
        while "LastEvaluatedKey" in page:
            page = table.scan(ConsistentRead=True, ExclusiveStartKey=page["LastEvaluatedKey"])
            items.extend(page.get("Items", []))
        if len(items) != 1:
            raise RuntimeError(f"Expected the single known test article; found {len(items)}")
        for item in items:
            status, actual = send("GET", "/articles/" + item["article_id"])
            assert status == 200 and actual == item
        if datafile.exists():
            raise RuntimeError("Backup already exists; refusing to overwrite it")
        datafile.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        result["article_count"] = len(items)
    elif args.phase == "logs":
        start = int(datetime.fromisoformat(json.loads((args.records / "failure.json").read_text())["time_utc"]).timestamp() * 1000)
        entries = session.client("logs").filter_log_events(
            logGroupName="/aws/lambda/" + name, startTime=start - 30000,
            filterPattern='"storage_failure_drill"', limit=20)
        matches = [e for e in entries.get("events", []) if "storage_failure_drill" in e["message"]]
        if not matches:
            raise RuntimeError("Drill log not visible yet")
        result["matched_logs"] = [{"timestamp": e["timestamp"], "message": e["message"]} for e in matches]
    else:
        items = json.loads(datafile.read_text(encoding="utf-8"))
        status, _ = send("GET", "/health", signed=False)
        assert status == 403, ("unsigned", status)
        status, _ = send("GET", "/health")
        assert status == 200, ("health", status)
        if args.phase == "rebuild":
            table = session.resource("dynamodb").Table(name)
            assert table.scan(Select="COUNT", ConsistentRead=True)["Count"] == 0
            mapping = []
            for old in items:
                status, _ = send("GET", "/articles/" + old["article_id"])
                assert status == 404
                status, created = send("POST", "/articles", {"title": old["title"], "content": old["content"]})
                assert status == 201
                status, actual = send("GET", "/articles/" + created["article_id"])
                assert status == 200 and actual == created
                assert actual["title"] == old["title"] and actual["content"] == old["content"]
                mapping.append({"previous_id": old["article_id"], "new_id": created["article_id"]})
            result["reloaded_articles"] = mapping
        else:
            for item in items:
                status, actual = send("GET", "/articles/" + item["article_id"])
                if args.phase == "failure":
                    assert status == 503 and actual["error"] == "service_unavailable"
                else:
                    assert status == 200 and actual == item
            result["articles_checked"] = len(items)
        result["unsigned_status"] = 403
        result["health_status"] = 200
        result["article_status"] = 503 if args.phase == "failure" else 200
    if args.target == "terraform" and state.exists():
        shutil.copy2(state, args.records / (args.phase + ".tfstate"))
    recordfile.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "matched_logs"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
