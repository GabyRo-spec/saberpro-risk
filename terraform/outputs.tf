output "api_url" {
  description = "URL base de la API (Lambda Function URL)."
  value       = aws_lambda_function_url.api.function_url
}

output "artifacts_bucket" {
  value = aws_s3_bucket.artifacts.id
}
