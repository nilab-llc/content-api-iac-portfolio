"""CDK CLI entry point. The exported template workflow uses scripts/synth_cdk.py."""
from aws_cdk import App
from content_stack import ContentStack, Settings

app = App(analytics_reporting=False)
failure = app.node.try_get_context("simulate_storage_failure") or "false"
if failure not in ("true", "false"):
    raise ValueError("simulate_storage_failure context must be true or false")
settings = Settings(
    memory_mb=int(app.node.try_get_context("memory_mb") or 128),
    log_retention_days=int(app.node.try_get_context("log_retention_days") or 7),
    simulate_storage_failure=failure == "true",
)
ContentStack(app, settings)
app.synth()
