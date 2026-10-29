"""Generate the deployable JSON template from the single shared Python source."""
import argparse
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "infra/cloudformation/template.json"


def sub(value):
    return {"Fn::Sub": value}


def ref(value):
    return {"Ref": value}


def template():
    code = (ROOT / "app/handler.py").read_text(encoding="utf-8")
    compile(code, "index.py", "exec")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("index.py", code)
    if len(archive.getvalue()) > 4 * 1024 * 1024:
        raise ValueError("Inline deployment ZIP exceeds 4 MiB")
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Personal content API portfolio - CloudFormation, generated from app/handler.py",
        "Parameters": {
            "MemoryMb": {"Type": "Number", "Default": 128, "AllowedValues": [128, 256, 512]},
            "LogRetentionDays": {"Type": "Number", "Default": 7, "AllowedValues": [1, 3, 7, 14, 30]},
            "SimulateStorageFailure": {"Type": "String", "Default": "false", "AllowedValues": ["false", "true"]},
        },
        "Rules": {
            "ApprovedTarget": {"Assertions": [
                {"Assert": {"Fn::Equals": [ref("AWS::AccountId"), "364561592630"]},
                 "AssertDescription": "Use the approved portfolio account"},
                {"Assert": {"Fn::Equals": [ref("AWS::Region"), "ap-northeast-1"]},
                 "AssertDescription": "Use Tokyo"},
            ]},
        },
        "Resources": {
            "Articles": {
                "Type": "AWS::DynamoDB::Table", "DeletionPolicy": "Delete", "UpdateReplacePolicy": "Delete",
                "Properties": {"TableName": "nilab-content-cfn", "BillingMode": "PAY_PER_REQUEST",
                    "AttributeDefinitions": [{"AttributeName": "article_id", "AttributeType": "S"}],
                    "KeySchema": [{"AttributeName": "article_id", "KeyType": "HASH"}]},
            },
            "ApiLogs": {
                "Type": "AWS::Logs::LogGroup", "DeletionPolicy": "Delete", "UpdateReplacePolicy": "Delete",
                "Properties": {"LogGroupName": "/aws/lambda/nilab-content-cfn", "RetentionInDays": ref("LogRetentionDays")},
            },
            "RuntimeRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {"RoleName": "nilab-content-cfn-runtime",
                    "PermissionsBoundary": sub("arn:${AWS::Partition}:iam::${AWS::AccountId}:policy/nilab-content-cfn-runtime-boundary"),
                    "AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": [{
                        "Effect": "Allow", "Action": "sts:AssumeRole", "Principal": {"Service": "lambda.amazonaws.com"}}]}},
            },
            "RuntimePolicy": {
                "Type": "AWS::IAM::RolePolicy",
                "Properties": {"RoleName": ref("RuntimeRole"), "PolicyName": "nilab-content-cfn-runtime",
                    "PolicyDocument": {"Version": "2012-10-17", "Statement": [
                        {"Effect": "Allow", "Action": ["dynamodb:GetItem", "dynamodb:PutItem"],
                         "Resource": {"Fn::GetAtt": ["Articles", "Arn"]}},
                        {"Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                         "Resource": sub("arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/nilab-content-cfn:*")},
                    ]}},
            },
            "ApiFunction": {
                "Type": "AWS::Lambda::Function", "DependsOn": ["RuntimePolicy", "ApiLogs"],
                "Properties": {"FunctionName": "nilab-content-cfn", "Runtime": "python3.13", "Handler": "index.handler",
                    "Role": {"Fn::GetAtt": ["RuntimeRole", "Arn"]}, "MemorySize": ref("MemoryMb"), "Timeout": 10,
                    "Code": {"ZipFile": code}, "Environment": {"Variables": {
                        "TABLE_NAME": ref("Articles"), "SIMULATE_STORAGE_FAILURE": ref("SimulateStorageFailure")}}},
            },
            "FunctionUrl": {
                "Type": "AWS::Lambda::Url",
                "Properties": {"TargetFunctionArn": {"Fn::GetAtt": ["ApiFunction", "Arn"]}, "AuthType": "AWS_IAM"},
            },
        },
        "Outputs": {
            "FunctionUrl": {"Value": {"Fn::GetAtt": ["FunctionUrl", "FunctionUrl"]}},
            "FunctionArn": {"Value": {"Fn::GetAtt": ["ApiFunction", "Arn"]}},
            "TableName": {"Value": ref("Articles")},
            "LogGroupName": {"Value": ref("ApiLogs")},
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if committed template differs; no writes")
    args = parser.parse_args()
    generated = json.dumps(template(), ensure_ascii=False, indent=2) + "\n"
    if len(generated.encode("utf-8")) > 51200:
        raise ValueError("Template exceeds the 51,200-byte direct TemplateBody limit")
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != generated:
            raise SystemExit("Template is stale; run python scripts/build_cloudformation.py")
        print("CloudFormation template is current; inline source matches app/handler.py")
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(generated, encoding="utf-8", newline="\n")
        print(f"Generated {TARGET.name}: {len(generated.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
