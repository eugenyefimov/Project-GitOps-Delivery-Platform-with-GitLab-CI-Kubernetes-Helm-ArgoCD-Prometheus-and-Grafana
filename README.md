# Platform App - Application Repository

Application repository for a two-repository GitOps delivery platform using GitLab CI/CD, Docker, Kubernetes, Helm, and ArgoCD.

## Problem This Project Solves

Typical CI pipelines build and deploy in the same system, which weakens auditability and increases deployment risk.  
This project separates responsibilities:

- application repository: build, test, scan, publish artifacts
- GitOps repository: deployment source of truth
- ArgoCD: reconciliation from Git to Kubernetes

The result is traceable, controlled, and reproducible delivery.

## Key Features

- two-repository GitOps architecture
- digest-based deployment updates (immutable release reference)
- branch-aware CI pipeline with controlled promotions
- external GitOps manifest validation during CI
- vulnerability scan in release path
- observability-ready service (`/livez`, `/readyz`, `/metrics`)

## Architecture Overview

- **This repository**
  - application code and tests
  - Docker image build/publish
  - CI automation to update external GitOps state
- **External GitOps repository**
  - Helm chart and environment values
  - ArgoCD Applications and deployment state
- **Cluster runtime**
  - ArgoCD syncs desired state from GitOps repo
  - Kubernetes runs the workloads
  - Prometheus/Grafana consume exposed metrics

## Architecture Diagram (Placeholder)

```text
[Developer Push]
      |
      v
[GitLab CI in App Repo]
  test -> build -> publish -> scan -> gitops update
      |
      v
[External GitOps Repo Commit]
      |
      v
[ArgoCD Reconciliation]
      |
      v
[Kubernetes Deployment]
      |
      v
[Prometheus Scrape] -> [Grafana Dashboards]
```

## CI/CD Flow

Pipeline stages:

- `test`
  - app tests with locked dependencies
  - Helm lint/template validation against external GitOps repo
- `build`
  - container build with traceable tags
- `publish`
  - image push to registry
  - digest capture
  - Trivy scan (strict on default branch/tags)
- `gitops_update`
  - `gitops_update_dev` automatic on default branch
  - `promote_staging` manual
  - `promote_prod` manual

Image traceability:

- `$CI_COMMIT_SHORT_SHA`
- `$CI_COMMIT_REF_SLUG-$CI_PIPELINE_IID`
- `latest` (default branch convenience only)
- `IMAGE_DIGEST` (`sha256:...`) used for deployment updates

## GitOps Flow

After image publish:

1. CI runs `ci/scripts/update_gitops_repo.py`
2. CI clones external GitOps repo using CI-provided credentials
3. CI updates target values file (default dev path: `charts/platform-app/values-dev.yaml`)
4. CI writes:
   - `image.repository`
   - `image.digest`
5. CI commits and pushes
6. ArgoCD detects Git change and syncs desired state to cluster

CI never applies manifests to Kubernetes directly.

## Environment Promotion Strategy

- **dev**: automatic GitOps update from default branch
- **staging**: manual promotion job
- **prod**: manual promotion job

This keeps feedback fast in dev and introduces explicit release control for higher environments.

## Observability Basics

The application exposes:

- `/livez` for liveness checks
- `/readyz` for readiness checks
- `/metrics` for Prometheus scraping

These endpoints support standard Kubernetes health management and Grafana dashboarding via Prometheus metrics.

## What This Project Demonstrates

- practical GitOps separation of concerns
- CI/CD design with controlled promotion boundaries
- immutable deployment references (digest-first)
- cross-repository automation without hardcoded secrets
- production-oriented baseline: security scan, health probes, metrics, structured logs

## Repository Contract (App Repo -> External GitOps Repo)

Expected files in the external GitOps repository:

- `charts/platform-app/values-dev.yaml`
- `charts/platform-app/values-staging.yaml`
- `charts/platform-app/values-prod.yaml`

Expected keys updated by CI:

- `image.repository`
- `image.digest`

Promotion and protection expectations:

- `gitops_update_dev` updates `values-dev.yaml` automatically from the default branch
- `promote_staging` and `promote_prod` are manual and should run under protected GitLab environments with approval rules

## Local Development

- runtime deps: `pip install -r requirements.lock`
- dev/test deps: `pip install -r requirements-dev.lock`
- run app: `python -m app.src.main`
- run tests: `pytest app/tests -q`
