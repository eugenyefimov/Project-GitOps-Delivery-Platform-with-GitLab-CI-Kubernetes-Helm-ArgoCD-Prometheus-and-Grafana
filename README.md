# Platform App - Application Repository

Application repository for a production-style two-repository GitOps delivery platform.

## Project Purpose

This repository owns the application lifecycle:

- source code and tests
- container build and publish
- CI automation that updates deployment state in an external GitOps repository

It does not own cluster manifests as source-of-truth and does not deploy directly to Kubernetes.

## Two-Repository Architecture

The platform is intentionally split into:

- **Application repository (this repo)**: build, test, scan, publish image, update GitOps state
- **GitOps repository (external remote repo)**: Helm values/manifests, ArgoCD Applications, environment deployment state

This separation is required for GitOps integrity:

- GitOps repository remains the single source of truth for desired cluster state
- CI credentials in app repo do not require direct cluster admin access
- deployment history is auditable as Git commits in deployment repo
- app delivery and cluster reconciliation are decoupled operationally

## CI Pipeline Flow

Pipeline stages:

- `test`: run unit/integration tests with locked dependencies
- `validate_gitops_manifests`: clone external GitOps repository and lint/render Helm chart for `dev`, `staging`, `prod`
- `build`: build container image and generate trace metadata
- `image_publish`: push tags and capture immutable digest
- `security_scan`: run Trivy scan before GitOps update jobs
- `gitops_update`:
  - `gitops_update_dev` (automatic on default branch)
  - `promote_staging` (manual)
  - `promote_prod` (manual)

## Image Build and Publish Flow

Each pipeline publishes:

- immutable commit tag: `$CI_COMMIT_SHORT_SHA`
- trace tag: `$CI_COMMIT_REF_SLUG-$CI_PIPELINE_IID`
- convenience tag: `latest` (default branch only)
- immutable digest: `sha256:...` (captured after push)

Digest is used as deployment truth to avoid mutable-tag drift.

## How CI Updates the External GitOps Repository

After publish, CI runs `ci/scripts/update_gitops_repo.py`:

1. clones external GitOps repo using secure CI credentials (`GITOPS_REPO_URL` + token)
2. updates target values file (default: `charts/platform-app/values-dev.yaml` in GitOps repo)
3. writes `image.repository` and `image.digest`
4. commits with release trace metadata
5. pushes to GitOps target branch

Staging and production updates use the same updater through manual promotion jobs.

For `dev`, the modified GitOps file is:

- `charts/platform-app/values-dev.yaml`

ArgoCD watches the GitOps repository branch and application path. When CI pushes this values change, ArgoCD detects drift and reconciles the cluster to the new desired image state.

This preserves GitOps principles because CI changes Git state only; ArgoCD performs the deployment reconciliation to Kubernetes.

## Why Deployment Is Handled by ArgoCD

CI must not deploy directly to Kubernetes in a GitOps model.

ArgoCD deploys by reconciling GitOps repository state to cluster state:

- pull-based reconciliation
- declarative drift correction
- auditable rollback via Git history
- reduced CI blast radius and credential exposure

## Key Technologies

- **GitLab CI/CD**: pipeline orchestration and promotions
- **Docker**: container build/package
- **Kubernetes**: runtime platform
- **Helm**: deployment packaging (in external GitOps repo)
- **ArgoCD**: GitOps reconciliation (from external GitOps repo)
- **Prometheus/Grafana**: metrics and visualization

## DevOps Capabilities Demonstrated

- strict two-repository GitOps boundary
- digest-based immutable release updates
- controlled promotion flow (`dev` -> `staging` -> `prod`)
- CI validation of external deployment manifests
- vulnerability scanning in release path
- least-privilege runtime and observability-ready app endpoints

## Practical Notes

- CI currently uses Docker-in-Docker for portability; production hardening path is BuildKit/Kaniko.
- Staging/production jobs should map to protected environments with approvals in GitLab settings.

## Dependency Reproducibility

- source definitions: `requirements.in`, `requirements-dev.in`
- hashed lock files: `requirements.lock`, `requirements-dev.lock`
- regenerate locks:
  - `python -m piptools compile --generate-hashes --output-file requirements.lock requirements.in`
  - `python -m piptools compile --generate-hashes --output-file requirements-dev.lock requirements-dev.in`

## Local Development

- runtime deps: `pip install -r requirements.lock`
- dev/test deps: `pip install -r requirements-dev.lock`
- run app: `python -m app.src.main`
- run tests: `pytest app/tests -q`
