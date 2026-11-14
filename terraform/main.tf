data "aws_caller_identity" "me" {}

# ---------------------------------------------------------------- S3: guarda el modelo (con versiones = recuperacion)
resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.project}-artifacts-${data.aws_caller_identity.me.account_id}"
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    id     = "borrar-versiones-viejas"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}

resource "aws_s3_object" "model" {
  bucket = aws_s3_bucket.artifacts.id
  key    = "models/model.json"
  source = "${path.module}/../api/model/model.json"
  etag   = filemd5("${path.module}/../api/model/model.json")
}

# ---------------------------------------------------------------- IAM: permisos minimos
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.project}-lambda"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "lambda" {
  statement {
    sid       = "LeerModelo"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.artifacts.arn}/models/*"]
  }
  statement {
    sid       = "EscribirLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.api.arn}:*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "${var.project}-lambda"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda.json
}

# ---------------------------------------------------------------- Lambda (FaaS) empaquetada como .zip, sin Docker ni ECR
data "archive_file" "api" {
  type        = "zip"
  source_file = "${path.module}/../api/app.py"
  output_path = "${path.module}/build/api.zip"
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.project}-api"
  retention_in_days = 14
}

resource "aws_lambda_function" "api" {
  function_name                  = "${var.project}-api"
  runtime                        = "python3.12"
  handler                        = "app.handler"
  role                           = aws_iam_role.lambda.arn
  filename                       = data.archive_file.api.output_path
  source_code_hash               = data.archive_file.api.output_base64sha256
  memory_size                    = var.lambda_memory_mb
  timeout                        = 10
  architectures                  = ["x86_64"]
  reserved_concurrent_executions = var.max_concurrency

  environment {
    variables = {
      MODEL_BUCKET = aws_s3_bucket.artifacts.id
      MODEL_KEY    = aws_s3_object.model.key
    }
  }
  depends_on = [aws_iam_role_policy.lambda, aws_cloudwatch_log_group.api]
}

# URL publica de la funcion (sin costo adicional, no necesita API Gateway)
resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
  cors {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST"]
    allow_headers = ["content-type"]
  }
}

# Desde octubre de 2025 una URL publica necesita DOS permisos (documentacion de AWS Lambda)
resource "aws_lambda_permission" "url_public" {
  statement_id           = "PermitirInvokeFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "url_public_invoke" {
  statement_id             = "PermitirInvokeFunction"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.api.function_name
  principal                = "*"
  invoked_via_function_url = true
}

# ---------------------------------------------------------------- alerta de costos
resource "aws_budgets_budget" "monthly" {
  name         = "${var.project}-mensual"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}
