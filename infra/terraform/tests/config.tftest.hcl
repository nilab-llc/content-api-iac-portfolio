mock_provider "aws" {}

run "safe_minimal_stack" {
  command = plan
  assert {
    condition     = aws_iam_role.api.permissions_boundary == "arn:aws:iam::364561592630:policy/nilab-content-tf-runtime-boundary"
    error_message = "Runtime role must retain its externally managed permission boundary."
  }
  assert {
    condition     = aws_lambda_function_url.api.authorization_type == "AWS_IAM"
    error_message = "Function URL must require IAM authentication."
  }
  assert {
    condition     = aws_dynamodb_table.articles.billing_mode == "PAY_PER_REQUEST"
    error_message = "Use the agreed on-demand billing mode."
  }
  assert {
    condition     = aws_lambda_function.api.environment[0].variables.SIMULATE_STORAGE_FAILURE == "false"
    error_message = "Failure drill must be disabled by default."
  }
  assert {
    condition     = length(local.invoke_policy.Statement) == 2 && local.invoke_policy.Statement[1].Condition.Bool["lambda:InvokedViaFunctionUrl"] == "true"
    error_message = "Invocation policy must cover both URL actions and restrict direct invocation."
  }
}

run "change_settings_without_replacing_table" {
  command = plan
  variables {
    memory_mb          = 256
    log_retention_days = 14
  }
  assert {
    condition     = aws_lambda_function.api.memory_size == 256 && aws_cloudwatch_log_group.api.retention_in_days == 14
    error_message = "Operational settings must be configurable."
  }
  assert {
    condition     = aws_dynamodb_table.articles.name == "nilab-content-tf"
    error_message = "Operational settings must not change the table identity."
  }
}

run "reject_invalid_memory" {
  command = plan
  variables {
    memory_mb = 129
  }
  expect_failures = [var.memory_mb]
}
