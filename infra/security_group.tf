resource "aws_security_group" "app" {
  name        = "hr-rag-app-sg"
  description = "HR RAG app -- inbound app port + SSH restricted to one CIDR"

  ingress {
    description = "App (HTTP)"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "hr-rag-app-sg"
  }
}
