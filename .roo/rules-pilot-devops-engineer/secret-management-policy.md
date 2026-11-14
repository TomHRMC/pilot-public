# 🔐 Secret Management Policy: Security Operational Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The "No-Hardcode" Mandate

The DevOps Engineer must ensure that **no secrets, API keys, or credentials** are ever stored in plain text within the repository, Dockerfiles, or environment variables in CI/CD scripts.

* **Detection**: Implement automated secret scanning (e.g., via GitHub Actions or Trivy) to block any commit containing strings that look like AWS keys or database URIs.

## 2. Mandatory Storage & Retrieval

All sensitive data must be stored and managed via **AWS Secrets Manager**.

* **Centralized Store**: Use Secrets Manager for the primary RDS password, QuickBooks client secrets, and Cognito client secrets.
* **KMS Encryption**: Every secret must be encrypted at rest using a customer-managed key (CMK) in **AWS KMS**.
* **Injection at Runtime**: ECS tasks and Lambda functions must fetch secrets at runtime using IAM roles; never bake secrets into the container image.

## 3. Automated Rotation Policy

To limit the impact of a potential credential leak, the DevOps Engineer must implement automated rotation:

* **RDS Passwords**: Configure Secrets Manager to rotate the PostgreSQL master password **quarterly** (target; not yet automated).
* **QuickBooks Tokens**: While OAuth tokens rotate via the application logic, the `Client Secret` must be manually rotated or managed through a secure lifecycle process.
* **IAM Access Keys**: Minimize the use of long-lived IAM keys; use **OIDC** for GitHub Actions to assume short-lived roles.

## 4. Access Control & Least Privilege

* **IAM Scoping**: ECS task roles must have `secretsmanager:GetSecretValue` permissions restricted to only the specific ARNs they require.
* **Audit Logging**: Enable **CloudTrail** logging for all Secrets Manager and KMS access (target; not yet in Terraform) to maintain a forensic trail of who accessed which secret.
* **Environment Isolation**: Secrets for `dev`, `staging`, and `production` must be strictly separated into different AWS accounts or via distinct naming prefixes with isolated IAM policies.

## 5. Secret Consumption Rules (FastAPI/App)

* **Pydantic Settings**: The application should use Pydantic's `BaseSettings` to load configurations, prioritizing environment variables injected from Secrets Manager.
* **Logging Redaction**: Ensure the logging framework (Structured JSON) is configured to never print the contents of sensitive configuration objects.
