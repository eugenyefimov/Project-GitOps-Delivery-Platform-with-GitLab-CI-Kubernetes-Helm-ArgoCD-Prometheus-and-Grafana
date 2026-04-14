# ArgoCD Configuration

This directory defines how ArgoCD watches and reconciles this GitOps repository.

## Applications

- `applications/platform-app-dev.yaml`
  - chart path: `charts/platform-app`
  - values file: `values-dev.yaml`
  - destination namespace: `platform-dev`
  - sync strategy: automated (`prune` + `selfHeal`)
- `applications/platform-app-staging.yaml`
  - chart path: `charts/platform-app`
  - values file: `values-staging.yaml`
  - destination namespace: `platform-staging`
  - sync strategy: manual sync (no `automated` block)
- `applications/platform-app-prod.yaml`
  - chart path: `charts/platform-app`
  - values file: `values-prod.yaml`
  - destination namespace: `platform-prod`
  - sync strategy: manual sync (no `automated` block)

## Sync model

- ArgoCD continuously watches the target Git revision (`main`) for each application.
- When Git changes are detected, ArgoCD computes drift between desired and live state.
- For `dev`, ArgoCD auto-applies drift corrections.
- For `staging` and `prod`, drift is visible but sync is intentionally operator-controlled.

## Why environment strategies differ

- `dev` favors speed and rapid feedback, so auto-sync is enabled.
- `staging` and `prod` favor release control, so sync is manually approved.
- This balances delivery velocity and operational safety.
