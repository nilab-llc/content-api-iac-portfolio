"""Prepare scoped CDK permission proposals, consolidating identical statement rules."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "permissions/cdk"


def many(value):
    return value if isinstance(value, list) else [value]


def atoms(policy):
    result = set()
    for statement in policy["Statement"]:
        if set(statement) - {"Sid", "Effect", "Action", "Resource", "Condition"}:
            raise ValueError("Unsupported statement form")
        condition = json.dumps(statement.get("Condition", {}), sort_keys=True)
        for action in many(statement["Action"]):
            for resource in many(statement["Resource"]):
                result.add((statement["Effect"], action, resource, condition))
    return result


def proposals():
    old = json.loads((ROOT / "permissions/cloudformation/sso-inline-merged-proposal.json").read_text())
    additions = json.loads((ROOT / "permissions/cloudformation/deploy-and-verify-additions.json").read_text().replace(
        "nilab-content-cfn", "nilab-content-cdk"))
    boundary = json.loads((ROOT / "permissions/cloudformation/runtime-boundary.json").read_text().replace(
        "nilab-content-cfn", "nilab-content-cdk"))
    groups = {}
    for statement in old["Statement"] + additions["Statement"]:
        key = (statement["Effect"], tuple(sorted(many(statement["Action"]))),
               json.dumps(statement.get("Condition", {}), sort_keys=True))
        if key not in groups:
            groups[key] = deepcopy(statement)
            groups[key]["Resource"] = []
        for resource in many(statement["Resource"]):
            if resource not in groups[key]["Resource"]:
                groups[key]["Resource"].append(resource)
    merged = {"Version": "2012-10-17", "Statement": list(groups.values())}
    for number, statement in enumerate(merged["Statement"], start=1):
        statement["Sid"] = f"ScopedRule{number:02d}"
    if atoms(merged) != atoms(old) | atoms(additions):
        raise ValueError("Consolidation changed permission scope")
    if len({s["Sid"] for s in merged["Statement"]}) != len(merged["Statement"]):
        raise ValueError("Duplicate statement IDs")
    if len(json.dumps(merged, separators=(",", ":"))) > 10240:
        raise ValueError("Permission-set inline non-whitespace limit exceeded")
    return {"runtime-boundary.json": boundary, "deploy-and-verify-additions.json": additions,
            "sso-inline-merged-proposal.json": merged}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, policy in proposals().items():
        rendered = json.dumps(policy, indent=2) + "\n"
        if len(rendered.encode()) > 32768:
            raise ValueError("Policy file exceeds 32,768 bytes")
        target = DIRECTORY / name
        if args.check:
            if not target.exists() or target.read_text() != rendered:
                raise SystemExit(f"Stale permission proposal: {name}")
        else:
            DIRECTORY.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8", newline="\n")
    print("CDK permission proposals verified; consolidated scope equals existing scope plus CDK additions")


if __name__ == "__main__":
    main()
