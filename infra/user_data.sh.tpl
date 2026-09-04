#!/bin/bash
set -e
exec > /var/log/hr-rag-bootstrap.log 2>&1

apt-get update
apt-get install -y ca-certificates curl gnupg git awscli

# Docker + Compose plugin, per Docker's official apt repo instructions
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

git clone ${repo_url} /opt/hr-rag
cd /opt/hr-rag

# Fetch the Anthropic API key from Secrets Manager via the instance's IAM
# role -- no static AWS credentials anywhere on this box.
API_KEY=$(aws secretsmanager get-secret-value --secret-id ${secret_id} --region ${region} --query SecretString --output text)
echo "ANTHROPIC_API_KEY=$API_KEY" > .env

docker compose up -d --build
