resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "hr-rag/anthropic-api-key"
  description = "Anthropic API key for the HR RAG portal"
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}
