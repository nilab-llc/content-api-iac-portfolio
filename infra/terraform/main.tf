locals {
  function_arn = "arn:aws:lambda:ap-northeast-1:${var.aws_account_id}:function:${var.name}"
  invoke_policy = {
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Action    = "lambda:InvokeFunctionUrl"
        Resource  = local.function_arn
        Condition = { StringEquals = { "lambda:FunctionUrlAuthType" = "AWS_IAM" } }
      },
      {
        Effect    = "Allow"
        Action    = "lambda:InvokeFunction"
        Resource  = local.function_arn
        Condition = { Bool = { "lambda:InvokedViaFunctionUrl" = "true" } }
      }
    ]
  }
}

resource "aws_dynamodb_table" "articles" {
  name         = var.name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "article_id"
  attribute {
    name = "article_id"
    type = "S"
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role" "api" {
  name                 = "${var.name}-runtime"
  permissions_boundary = "arn:aws:iam::${var.aws_account_id}:policy/${var.name}-runtime-boundary"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "runtime" {
  name = "${var.name}-runtime"
  role = aws_iam_role.api.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem"]
        Resource = aws_dynamodb_table.articles.arn
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.api.arn}:*"
      }
    ]
  })
}

data "archive_file" "app" {
  type        = "zip"
  source_file = "${path.module}/../../app/handler.py"
  output_path = "${path.module}/app.zip"
}

resource "aws_lambda_function" "api" {
  function_name    = var.name
  role             = aws_iam_role.api.arn
  runtime          = "python3.13"
  handler          = "handler.handler"
  filename         = data.archive_file.app.output_path
  source_code_hash = data.archive_file.app.output_base64sha256
  memory_size      = var.memory_mb
  timeout          = 10
  environment {
    variables = {
      TABLE_NAME               = aws_dynamodb_table.articles.name
      SIMULATE_STORAGE_FAILURE = tostring(var.simulate_storage_failure)
    }
  }
  depends_on = [aws_iam_role_policy.runtime, aws_cloudwatch_log_group.api]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "AWS_IAM"
}
