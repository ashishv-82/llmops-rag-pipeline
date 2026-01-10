terraform {
  required_providers {
    helm = {
      source = "hashicorp/helm"
    }
    kubernetes = {
      source = "hashicorp/kubernetes"
    }
  }
}

resource "helm_release" "kube_prometheus_stack" {
  name             = "prometheus"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = var.namespace
  create_namespace = true
  version          = "56.0.0"

  values = [
    file("${path.module}/values.yaml")
  ]

  set {
    name  = "grafana.adminPassword"
    value = var.grafana_password
  }
  set {
    name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
    value = "false"
  }
  set {
    name  = "grafana.service.type"
    value = "LoadBalancer"
  }
}

resource "kubernetes_config_map" "rag_metrics_dashboard" {
  metadata {
    name      = "rag-metrics-dashboard"
    namespace = var.namespace
    labels = {
      grafana_dashboard = "1"
    }
  }

  data = {
    "rag_metrics.json" = file("${path.module}/dashboards/rag_metrics.json")
  }

  depends_on = [helm_release.kube_prometheus_stack]
}
