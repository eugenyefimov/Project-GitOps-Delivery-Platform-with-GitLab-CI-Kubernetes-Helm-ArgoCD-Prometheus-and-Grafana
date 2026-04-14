# Platform App - Application Repository

Production-style application repository for a GitOps delivery platform built with GitLab CI/CD, Docker, Kubernetes, Helm, ArgoCD, Prometheus, and Grafana.

## Project Purpose

This repository demonstrates a clean separation between:

- application lifecycle (build, test, package, publish)
- deployment lifecycle (GitOps state managed in a separate repository)

The goal is an interview-defensible, realistic DevOps workflow where every release is traceable from commit to running workload.

## Architecture Role of This Repository

This is the **application repository**. It owns:

- application source code and tests
- container build definition
- CI/CD automation that publishes the image
- CI logic that updates deployment state in the separate GitOps repository

It does **not** own direct Kubernetes deployment. Cluster reconciliation is delegated to ArgoCD.

## CI Pipeline Flow

Pipeline stages:

- `test`: run unit/integration tests with locked development dependencies
- `validate_gitops_manifests`: clone GitOps repo and lint/render Helm chart for `dev`, `staging`, `prod`
- `build`: build image and produce trace metadata
- `image_publish`: push tags and capture immutable image digest
- `security_scan`: run Trivy vulnerability scan before any GitOps update
- `gitops_update` jobs:
  - `gitops_update_dev` (automatic on default branch)
  - `promote_staging` (manual)
  - `promote_prod` (manual)

## Image Build and Publish Flow

Each pipeline publishes:

- immutable commit tag: `$CI_COMMIT_SHORT_SHA`
- trace tag: `$CI_COMMIT_REF_SLUG-$CI_PIPELINE_IID`
- convenience tag: `latest` (default branch only)
- immutable digest: `sha256:...` (captured after push)

The digest is the deployment source of truth used for GitOps updates.

## How the GitOps Repository Gets Updated

After image publish, CI runs `ci/scripts/update_gitops_repo.py` to:

1. clone the GitOps repository using CI-provided credentials
2. update target environment values file (default: `charts/platform-app/values-dev.yaml`)
3. write `image.repository` and `image.digest` with published artifact metadata
4. commit with deployment trace metadata (app, env, source commit, pipeline)
5. push to GitOps target branch

Staging and production updates use the same mechanism through manual promotion jobs.

## Why ArgoCD Deploys Instead of CI

Direct CI-to-cluster deployment is intentionally avoided.

ArgoCD deploys from Git because it provides:

- declarative desired state
- pull-based reconciliation
- auditable deployment history in Git
- deterministic rollback via Git revert

This preserves GitOps principles and reduces CI blast radius.

## Key Technologies

- **GitLab CI/CD**: pipeline orchestration, artifact flow, promotion controls
- **Docker**: non-root runtime image build and packaging
- **Helm**: Kubernetes application templating with env-specific values
- **ArgoCD**: GitOps reconciliation and environment deployment control
- **Prometheus**: metrics scraping from `/metrics`
- **Grafana**: metrics visualization and operational dashboards

## DevOps Capabilities Demonstrated

- two-repository GitOps architecture (app repo + GitOps repo)
- immutable release strategy with digest-based deployments
- promotion model across `dev`, `staging`, `prod`
- CI validation of deployment manifests before promotion
- security baseline with vulnerability scanning and least-privilege runtime
- observability-ready application behavior (health, readiness, metrics, structured logs)

## Practical Delivery Notes

- CI currently uses Docker-in-Docker for portability in a portfolio setup.
- This is an intentional temporary trade-off; a production hardening path is migrating image build/push to BuildKit or Kaniko runners.
- Staging and production promotion jobs are mapped to GitLab environments and should be protected with approval rules.

## Dependency Lock Strategy

- Source dependency definitions are maintained in:
  - `requirements.in`
  - `requirements-dev.in`
- Reproducible lock files are generated with hashes:
  - `requirements.lock`
  - `requirements-dev.lock`
- Regenerate locks with:
  - `python -m piptools compile --generate-hashes --output-file requirements.lock requirements.in`
  - `python -m piptools compile --generate-hashes --output-file requirements-dev.lock requirements-dev.in`

## Local Development

- Runtime deps: `pip install -r requirements.lock`
- Dev/test deps: `pip install -r requirements-dev.lock`
- Run app: `python -m app.src.main`
- Run tests: `pytest app/tests -q`
