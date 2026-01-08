variable "namespace" {
  description = "Namespace to deploy monitoring stack"
  type        = string
  default     = "monitoring"
}

variable "grafana_password" {
  description = "Admin password for Grafana"
  type        = string
  sensitive   = true
}
