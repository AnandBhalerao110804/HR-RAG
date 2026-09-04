data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app_instance" {
  name               = "hr-rag-app-instance-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

# Least-privilege: only allowed to read the one secret this app needs, not
# broad Secrets Manager access.
data "aws_iam_policy_document" "secrets_access" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.anthropic_api_key.arn]
  }
}

resource "aws_iam_role_policy" "secrets_access" {
  name   = "hr-rag-secrets-access"
  role   = aws_iam_role.app_instance.id
  policy = data.aws_iam_policy_document.secrets_access.json
}

resource "aws_iam_instance_profile" "app_instance" {
  name = "hr-rag-app-instance-profile"
  role = aws_iam_role.app_instance.name
}
