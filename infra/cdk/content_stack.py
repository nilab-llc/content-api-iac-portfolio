"""CDK-defined content API. No assets, lookups, bootstrap or AWS calls at synthesis."""
from dataclasses import dataclass
from pathlib import Path

from aws_cdk import (
    App, CfnOutput, Environment, LegacyStackSynthesizer, RemovalPolicy, Stack,
    aws_dynamodb as dynamodb, aws_iam as iam, aws_lambda as lambda_, aws_logs as logs,
)
from constructs import Construct

ROOT = Path(__file__).resolve().parents[2]
NAME = "nilab-content-cdk"
ACCOUNT = "364561592630"
REGION = "ap-northeast-1"


@dataclass(frozen=True)
class Settings:
    memory_mb: int = 128
    log_retention_days: int = 7
    simulate_storage_failure: bool = False

    def __post_init__(self):
        if type(self.memory_mb) is not int or self.memory_mb not in (128, 256, 512):
            raise ValueError("memory_mb must be 128, 256 or 512")
        if type(self.log_retention_days) is not int or self.log_retention_days not in (1, 3, 7, 14, 30):
            raise ValueError("log_retention_days must be 1, 3, 7, 14 or 30")
        if type(self.simulate_storage_failure) is not bool:
            raise ValueError("simulate_storage_failure must be a boolean")


class ContentStack(Stack):
    def __init__(self, scope: Construct, settings: Settings):
        super().__init__(scope, NAME, stack_name=NAME,
            env=Environment(account=ACCOUNT, region=REGION),
            description="Personal content API portfolio - AWS CDK",
            synthesizer=LegacyStackSynthesizer(), analytics_reporting=False)
        table = dynamodb.Table(self, "Articles", table_name=NAME,
            partition_key=dynamodb.Attribute(name="article_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST, removal_policy=RemovalPolicy.DESTROY)
        retention = {1: logs.RetentionDays.ONE_DAY, 3: logs.RetentionDays.THREE_DAYS,
            7: logs.RetentionDays.ONE_WEEK, 14: logs.RetentionDays.TWO_WEEKS, 30: logs.RetentionDays.ONE_MONTH}
        log_group = logs.LogGroup(self, "ApiLogs", log_group_name="/aws/lambda/" + NAME,
            retention=retention[settings.log_retention_days], removal_policy=RemovalPolicy.DESTROY)
        role = iam.Role(self, "RuntimeRole", role_name=NAME + "-runtime",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            permissions_boundary=iam.ManagedPolicy.from_managed_policy_arn(self, "RuntimeBoundary",
                f"arn:aws:iam::{ACCOUNT}:policy/{NAME}-runtime-boundary"))
        # Explicit policy and Lambda L1 avoid implicit broad logging grants/custom resources.
        policy = iam.CfnRolePolicy(self, "RuntimePolicy", role_name=role.role_name, policy_name=NAME + "-runtime",
            policy_document={"Version": "2012-10-17", "Statement": [
                {"Effect": "Allow", "Action": ["dynamodb:GetItem", "dynamodb:PutItem"], "Resource": table.table_arn},
                {"Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                 "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/aws/lambda/{NAME}:*"},
            ]})
        source = (ROOT / "app/handler.py").read_text(encoding="utf-8")
        compile(source, "index.py", "exec")
        function = lambda_.CfnFunction(self, "ApiFunction", function_name=NAME,
            runtime="python3.13", handler="index.handler", role=role.role_arn,
            memory_size=settings.memory_mb, timeout=10, code=lambda_.CfnFunction.CodeProperty(zip_file=source),
            environment=lambda_.CfnFunction.EnvironmentProperty(variables={
                "TABLE_NAME": table.table_name,
                "SIMULATE_STORAGE_FAILURE": str(settings.simulate_storage_failure).lower(),
            }))
        function.add_resource_dependency(policy)
        function.add_resource_dependency(log_group.node.default_child)
        url = lambda_.CfnUrl(self, "FunctionUrl", target_function_arn=function.attr_arn, auth_type="AWS_IAM")
        CfnOutput(self, "FunctionUrlOutput", value=url.attr_function_url)
        CfnOutput(self, "FunctionArn", value=function.attr_arn)
        CfnOutput(self, "TableName", value=table.table_name)
        CfnOutput(self, "LogGroupName", value=log_group.log_group_name)


def synthesize(settings=Settings(), outdir=None):
    app = App(outdir=outdir, analytics_reporting=False, context={"aws:cdk:enable-path-metadata": False})
    stack = ContentStack(app, settings)
    assembly = app.synth()
    artifact = assembly.get_stack_by_name(stack.stack_name)
    return artifact.template, assembly
