# Platform App GitOps Mapping

This directory documents how `platform-app` is represented in this GitOps repository.

- Helm chart source: `charts/platform-app/`
- Environment values:
  - `charts/platform-app/values-dev.yaml`
  - `charts/platform-app/values-staging.yaml`
  - `charts/platform-app/values-prod.yaml`
- Environment namespaces:
  - `platform-dev`
  - `platform-staging`
  - `platform-prod`

The application repository CI updates `image.repository` and `image.digest` in the target environment values file.
