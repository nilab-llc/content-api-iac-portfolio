output "function_url" {
  value = aws_lambda_function_url.api.function_url
}

output "log_group" {
  value = aws_cloudwatch_log_group.api.name
}

output "table_name" {
  value = aws_dynamodb_table.articles.name
}

output "invoker_policy_json" {
  description = "Review-only policy for a same-account caller. Does not grant or attach permissions."
  value       = jsonencode(local.invoke_policy)
}
