# Terraform IaC — MyceliumFractalNet

This module bootstraps the namespace and service account used by the production Kubernetes deployment.
Use it as a foundation for extending infrastructure provisioning (networking, clusters, secrets, and observability) in a reproducible, version-controlled manner.

## Usage

```bash
terraform init
terraform plan -var="kubeconfig_path=~/.kube/config"
terraform apply -var="kubeconfig_path=~/.kube/config"
```

## Next steps (recommended)

- Add cluster provisioning (EKS/GKE/AKS) in a separate stack.
- Integrate secret management (Vault/Secrets Manager) with Terraform-managed policies.
- Add network policy baselines and ingress controllers as Terraform-managed modules.
