# Observability Integration

This repository enables monitoring integration for the application without deploying a full monitoring stack.

## What is implemented here

- Application metrics endpoint (`/metrics`) is exposed by the app.
- Helm chart applies common Prometheus scrape annotations on Pod and Service.
- Helm chart includes optional `ServiceMonitor` support:
  - template: `charts/platform-app/templates/servicemonitor.yaml`
  - values switch: `serviceMonitor.enabled`

## What is assumed to exist in the cluster

- Prometheus is already installed and configured to scrape annotated targets, or
- Prometheus Operator is installed if `ServiceMonitor` is enabled.
- Grafana is installed and connected to Prometheus as a data source.

This repo does not install Prometheus, Grafana, or operators in the current scope.

## Prometheus scrape options

- Annotation-based scrape (default-friendly):
  - `prometheus.io/scrape: "true"`
  - `prometheus.io/path: "/metrics"`
  - `prometheus.io/port: "8080"`
- ServiceMonitor-based scrape (operator environments):
  - set `serviceMonitor.enabled: true`
  - optionally set extra labels in `serviceMonitor.labels` to match Prometheus selectors

## Grafana visualization guidance

Recommended starter panels (portfolio-ready):

- Request rate:
  - `sum(rate(platform_app_http_requests_total[5m])) by (endpoint, status_code)`
- Error rate (5xx):
  - `sum(rate(platform_app_http_requests_total{status_code=~"5.."}[5m]))`
- Request latency (p95):
  - `histogram_quantile(0.95, sum(rate(platform_app_http_request_duration_seconds_bucket[5m])) by (le))`
- In-flight requests:
  - `platform_app_in_flight_requests`

These queries are enough to demonstrate service health and runtime behavior in interviews.
