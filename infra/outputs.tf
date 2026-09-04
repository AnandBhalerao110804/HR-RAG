output "public_ip" {
  description = "Public IP of the HR RAG app instance"
  value       = aws_eip.app.public_ip
}

output "app_url" {
  description = "URL to access the HR RAG portal"
  value       = "http://${aws_eip.app.public_ip}:8000"
}
