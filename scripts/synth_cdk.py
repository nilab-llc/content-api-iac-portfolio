"""Export a small deployable template from actual CDK constructs; no AWS access."""
import argparse
import io
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "infra/cdk"))
from content_stack import Settings, synthesize


def render(settings):
    with tempfile.TemporaryDirectory(prefix="content-cdk-") as directory:
        template, assembly = synthesize(settings, outdir=directory)
        # No asset manifests: no S3/ECR publish step or bootstrap-dependent assets.
        manifest = json.loads((Path(directory) / "manifest.json").read_text(encoding="utf-8"))
        for artifact in manifest.get("artifacts", {}).values():
            if artifact["type"] == "cdk:asset-manifest":
                raise ValueError("Unexpected CDK asset manifest")
        functions = [r for r in template["Resources"].values() if r["Type"] == "AWS::Lambda::Function"]
        if len(functions) != 1:
            raise ValueError("Expected one Lambda")
        source = functions[0]["Properties"]["Code"]["ZipFile"]
        if source != (ROOT / "app/handler.py").read_text(encoding="utf-8"):
            raise ValueError("Inline source differs from shared application")
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
            package.writestr("index.py", source)
        if len(archive.getvalue()) > 4 * 1024 * 1024:
            raise ValueError("Inline ZIP exceeds 4 MiB")
        result = json.dumps(template, ensure_ascii=False, indent=2) + "\n"
        if len(result.encode("utf-8")) > 51200:
            raise ValueError("Template exceeds direct TemplateBody size")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-mb", type=int, default=128)
    parser.add_argument("--log-retention-days", type=int, default=7)
    parser.add_argument("--simulate-storage-failure", choices=["true", "false"], default="false")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    settings = Settings(args.memory_mb, args.log_retention_days, args.simulate_storage_failure == "true")
    if settings != Settings() and args.output is None:
        parser.error("Non-default settings require --output to preserve the committed baseline")
    target = args.output or ROOT / "infra/cdk/template.json"
    result = render(settings)
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != result:
            raise SystemExit("CDK template is stale; run python scripts/synth_cdk.py")
        print("CDK template is current; shared source and asset exclusion verified")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result, encoding="utf-8", newline="\n")
        print(f"Generated {target.name}: {len(result.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
