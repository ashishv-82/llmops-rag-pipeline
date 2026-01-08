output "grafana_admin_password" {
  description = "The admin password for Grafana (sensitive)"
  value       = var.grafana_password
  sensitive   = true
}

output "namespace" {
  description = "The namespace where the monitoring stack is deployed"
  value       = var.namespace
}
