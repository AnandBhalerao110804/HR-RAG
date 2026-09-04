# Resolved at apply time rather than a hardcoded AMI ID -- AMI IDs are
# region- and time-specific, a hardcoded one would silently go stale.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app_instance.name

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    repo_url  = var.repo_url
    secret_id = aws_secretsmanager_secret.anthropic_api_key.id
    region    = var.region
  })

  tags = {
    Name = "hr-rag-app"
  }
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = {
    Name = "hr-rag-app-eip"
  }
}
