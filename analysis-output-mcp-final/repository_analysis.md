# Repository Intelligent Analysis Report

## 1. Repository Summary

- **Repository:** gc-sre-eks-src
- **Source:** https://github.com/NBCUDTC/gc-sre-eks-src.git
- **Source Type:** GitHub
- **Repository Type:** Application / Service / Library Repository
- **Files Analyzed:** 85
- **Local LLM Status:** Skipped by command line

### What the Application / Repository Does

This module is for creating an EKS Cluster in AWS using Kubernetes v1.28. The AMI release version for workers will default to the latest version which matches the eksmasterversion. ⚠️ Breaking change in v1.34: Amazon Linux 2023 (AL2023) support has been removed. Bottlerocket is now the only supported AMI type. - Review the amitype currently used by every EKS node group in your Terragrunt/Terraform - Ensure all node groups are set to BOTTLEROCKETx8664 or BOTTLEROCKETARM64. - Any node group that previously relied on the AL2023 default (i.e. had no explicit amitype) will be destroyed and recreated with a Bottlerocket AMI on the next terraform apply. Plan for a rolling node replacement or pin the value before upgrading. Bottlerocket was chosen as the sole AMI because of its stronger security posture, minimal attack surface, and Kubernetes-focused design: it ships only the packages required to run containers, applies automatic OS updates atomically with rollback support, and enforces read-only root filesystem and SELinux policies out of the box.

### Repository Summary

This module is for creating an EKS Cluster in AWS using Kubernetes v1.28. The AMI release version for workers will default to the latest version which matches the eksmasterversion. ⚠️ Breaking change in v1.34: Amazon Linux 2023 (AL2023) support has been removed. Bottlerocket is now the only supported AMI type. - Review the amitype currently used by every EKS node group in your Terragrunt/Terraform - Ensure all node groups are set to BOTTLEROCKETx8664 or BOTTLEROCKETARM64. - Any node group that previously relied on the AL2023 default (i.e. had no explicit amitype) will be destroyed and recreated with a Bottlerocket AMI on the next terraform apply. Plan for a rolling node replacement or pin the value before upgrading. Bottlerocket was chosen as the sole AMI because of its stronger security posture, minimal attack surface, and Kubernetes-focused design: it ships only the packages required to run containers, applies automatic OS updates atomically with rollback support, and enforces read-only root filesystem and SELinux policies out of the box.

## 2. Technology Stack

- **Languages:** Terraform, Go, Shell
- **Frameworks:** Not detected
- **Runtime:** Not detected
- **Databases:** Not detected
- **Cloud Platforms:** Not detected
- **Containers:** Not detected
- **Kubernetes Helm Terraform:** Terraform
- **Ci Cd:** GitHub Actions
- **Testing Tools:** Not detected
- **Monitoring Observability:** Not detected
- **Important Core Libraries:** Not detected

## 3. Repository Scan and Engineering Artifacts

- **Important files:** .github/workflows/pre-commit.yml, .github/workflows/release.yml, .pre-commit-config.yaml, README.md

- **Configuration:** config/eks_vpc_cni_config.json
- **Docker:** Not detected
- **Kubernetes Helm:** Not detected
- **Terraform:** calico.tf, cluster_auth.tf, eip.tf, eks_addons.tf, eni_configs.tf, examples/aws/main.tf, examples/aws/outputs.tf, examples/aws/providers.tf, examples/aws/variables.tf, firewall.tf, fluentbit.tf, iam_bibcd.tf, ip_masq_agent.tf, main.tf, modules/aws_auth/aws_auth.tf, modules/aws_auth/providers.tf, modules/aws_auth/variables.tf, modules/calico/main.tf, modules/calico/providers.tf, modules/ebs_csi_controller/ebs-csi-permissions.tf, modules/ebs_csi_controller/outputs.tf, modules/ebs_csi_controller/providers.tf, modules/ebs_csi_controller/storage-class.tf, modules/ebs_csi_controller/variables.tf, modules/eks_bibcd_roles/iam.tf, modules/eks_bibcd_roles/outputs.tf, modules/eks_bibcd_roles/providers.tf, modules/eks_bibcd_roles/variables.tf, modules/eks_workers_with_cni_secondary_cidr/main.tf, modules/eks_workers_with_cni_secondary_cidr/providers.tf, modules/eks_workers_with_cni_secondary_cidr/user_data.tf, modules/eks_workers_with_cni_secondary_cidr/variables.tf, networks.tf, outputs.tf, providers.tf, system_namespaces.tf, tests/deploy_current_release/aws/main.tf, tests/deploy_current_release/aws/outputs.tf, tests/deploy_current_release/aws/providers.tf, tests/deploy_current_release/aws/variables.tf, variables.tf, workers.tf
- **Ci Cd:** .github/workflows/pre-commit.yml, .github/workflows/release.yml
- **Api Specs:** Not detected
- **Documentation:** README.md, docs/module_details.md, examples/aws/README.md, modules/aws_auth/README.md, modules/calico/README.md, modules/ebs_csi_controller/README.md, modules/eks_bibcd_roles/README.md, modules/eks_workers_with_cni_secondary_cidr/README.md, tests/README.md, tests/deploy_current_release/aws/README.md

## 4. Main Components and Code Structure

### modules
Top-level source/component area; semantic responsibility refined by local LLM
**Evidence:** 29 analyzed core files under modules/

### .github
Top-level source/component area; semantic responsibility refined by local LLM
**Evidence:** 5 analyzed core files under .github/

### manifests
Top-level source/component area; semantic responsibility refined by local LLM
**Evidence:** 3 analyzed core files under manifests/

### config
Configuration
**Evidence:** 1 analyzed core files under config/

## 5. Code Architecture

- **Architecture Style:** Modular repository architecture
- **Architecture Explanation:** The repository follows a modular repository architecture. Static analysis identified 4 major structural component areas, 0 executable/package entry points, and 0 repository-local dependency relationships. The architecture below is generated from source layout, imports, symbols, package metadata and executable entry points; the local LLM is used only to explain these facts in repository-specific language.

### Layers / Modules

| Layer / Module | Description | Evidence |
| --- | --- | --- |
| modules | Top-level source/component area; semantic responsibility refined by local LLM | 29 analyzed core files under modules/ |
| .github | Top-level source/component area; semantic responsibility refined by local LLM | 5 analyzed core files under .github/ |
| manifests | Top-level source/component area; semantic responsibility refined by local LLM | 3 analyzed core files under manifests/ |
| config | Configuration | 1 analyzed core files under config/ |

### Entry Points

_Not detected._

### Major Components

| Component | Responsibility | Evidence |
| --- | --- | --- |
| modules | Top-level source/component area; semantic responsibility refined by local LLM | 29 analyzed core files under modules/ |
| .github | Top-level source/component area; semantic responsibility refined by local LLM | 5 analyzed core files under .github/ |
| manifests | Top-level source/component area; semantic responsibility refined by local LLM | 3 analyzed core files under manifests/ |
| config | Configuration | 1 analyzed core files under config/ |

### Component Relationships

_Not detected._

### Configuration Model

Repository contains explicit configuration artifacts: config/eks_vpc_cni_config.json.

### Extension Points

- modules/aws_auth/providers.tf
- modules/calico/providers.tf
- modules/ebs_csi_controller/providers.tf
- modules/eks_bibcd_roles/providers.tf
- modules/eks_workers_with_cni_secondary_cidr/providers.tf
- providers.tf

### Deployment Model

Terraform-managed infrastructure

### Architecture Data / Control Flow

1. No single executable entry point was found; this repository is likely consumed as a library/framework or exposes multiple integration entry points.
2. Configuration artifacts influence component initialization and runtime behavior.
3. Core components process requests/commands/events through repository modules and return results to the caller or downstream integration.

## 6. Overall Code Flow

- **Code Flow Analysis Status:** Deterministic static code-flow fallback (--skip-llm)

This section explains the repository flow in simple execution order. It separates the main runtime from independent automation/tooling paths and only uses code/source evidence found in the repository.

### Flow Overview

The repository runtime starts from its executable entry point, loads configuration and infrastructure dependencies, registers production routes, and starts the service. Each request then follows the statically resolved handler -> use case/service -> repository -> DAL/client path where such a chain is proven. Persistence operations are shown only when directly detected in source. The service closes through its graceful shutdown path when one is present.

### Application Startup Flow

#### Step 1: Load runtime configuration

The application uses the detected configuration files during startup. Configuration values control later runtime initialization; values not proven from source are not guessed.

**Code / files involved:**
- `config/eks_vpc_cni_config.json`

**What happens next:** Validated runtime settings are available to the bootstrap code.

**Evidence:** config/eks_vpc_cni_config.json

### Static Call / Module Paths

The paths below are the exact callable/import chains that static analysis could prove. They support the simplified flow above.

No complete callable chain was statically provable for this repository.

## 7. Dependencies and Compatibility

Dependencies are grouped by scope. Example/test/documentation dependencies do not contaminate the core technology stack.

## 8. Tests and Coverage

- **Testing frameworks:** Not detected
- **Test files detected:** 13
- **Coverage status:** Actual coverage result not found
- **Coverage percentage:** Not available
- **Coverage source:** Not available

## 9. Production Internal APIs

_Test/mock/example routes are excluded._

_Not detected._

## 10. Production External API and Integration Calls

_Test/mock/example calls are excluded._

_Not detected._

## 11. Main Use Cases

No high-level use cases were returned by the local LLM.

## 12. Analysis Limitations

- Local LLM skipped; deterministic architecture and detailed static code flow are still reported.
