# Platform GitOps Repository

Deployment source of truth for a production-style GitOps platform.

## Project Purpose

This repository defines the desired Kubernetes state for the application across `dev`, `staging`, and `prod`.

It exists to separate deployment control from application build pipelines, provide a clear audit trail, and enable predictable, Git-driven operations.

## GitOps Model

This project uses a pull-based GitOps model:

1. Application CI builds and publishes a container image.
2. CI commits a deployment-state change in this repository (image digest update).
3. ArgoCD detects the Git change and reconciles cluster state to match.

CI does not deploy directly to Kubernetes. Git is the control plane for delivery state.

## Role of Helm

Helm is the deployment packaging mechanism:

- chart source lives in `charts/platform-app/`
- shared defaults are defined in `values.yaml`
- environment overlays are defined in `values-dev.yaml`, `values-staging.yaml`, `values-prod.yaml`

This keeps manifests consistent while allowing controlled environment differences.

## Role of ArgoCD

ArgoCD is the deployment reconciler:

- `argocd/projects/` defines project boundaries and allowed deployment scope
- `argocd/applications/` defines environment-specific Applications

ArgoCD continuously compares live cluster state with this repository and applies declared drift policy:

- `dev`: automated sync for fast feedback
- `staging`/`prod`: controlled sync strategy for release governance

## Environment Separation

Environments are explicitly separated by values and target namespaces:

- `dev` -> `platform-dev`
- `staging` -> `platform-staging`
- `prod` -> `platform-prod`

Promotion is commit-driven (`dev` -> `staging` -> `prod`), not manual `kubectl` mutation.

## How CI Updates This Repository

The application repository pipeline updates this repository by:

- targeting an environment values file (for example `charts/platform-app/values-dev.yaml`)
- writing an immutable `image.digest` value
- committing with trace metadata (source commit, pipeline, environment)

This gives deterministic release tracking and rollback via Git history.

## How ArgoCD Sync Works

After CI pushes a GitOps commit:

1. ArgoCD polls/watches the configured branch.
2. It renders Helm with the environment values file.
3. It computes drift against live cluster resources.
4. It syncs according to application sync policy (auto or manual).

Every deployed state is tied to a Git commit and reconciled declaratively.

## Repository Structure

- `charts/platform-app/`: Helm chart and environment values
- `environments/`: environment namespace/manifests
- `argocd/projects/`: ArgoCD project guardrails
- `argocd/applications/`: ArgoCD app definitions per environment
- `observability/`: Prometheus/Grafana integration guidance
- `apps/platform-app/`: app mapping and ownership metadata

## Practices Demonstrated

- strict separation of app build pipeline and deployment state
- immutable, digest-based release management
- environment-aware promotion and deployment control
- declarative reconciliation with ArgoCD
- least-privilege deployment boundaries via ArgoCD project policy
- auditable, rollback-friendly operations using Git history
