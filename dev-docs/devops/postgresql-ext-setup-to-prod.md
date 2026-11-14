# PostgreSQL VS Code Extension — PROD Connection Setup

**Purpose**: Step-by-step guide to connect the VS Code PostgreSQL extension to the production RDS instance via SSH tunnel through the bastion host.  
**Prereq**: You already have a local DB connection working in the extension. This adds a second connection for PROD.

---

## How It Works

The PROD RDS instance lives in a **private subnet** with no public internet access. The only way in is through the bastion host:

```
Your Mac (localhost:5433)
   ↓  SSH tunnel (via ~/.ssh/pilot_admin_ed25519)
Bastion Host (203.0.113.12 — Elastic IP)
   ↓  Private VPC routing
RDS PostgreSQL (pilot-production — private subnet, port 5432)
```

> **Why port 5433 locally?** Your local dev DB already uses `localhost:5432`. The tunnel binds to `5433` instead to avoid a port conflict.

---

## Prerequisites

Before connecting, confirm these are in place:

- [ ] `~/.ssh/pilot_admin_ed25519` private key exists on your Mac
- [ ] `~/.ssh/config` has the `pilot-bastion` host alias (see [aws-ops-runbook.md §6](aws-ops-runbook.md))
- [ ] Bastion is **running** (start it via your AWS profile scripts if needed)
- [ ] Your current IP is in the bastion's security group (`sg-bastion`)
- [ ] AWS CLI is configured — your `~/.aws/config` uses the `default` profile (IAM user: `pilot-admin`); no `--profile` flag needed in any command below

---

## Step 1 — Fetch the RDS Endpoint

The RDS endpoint is a **sensitive Terraform output** — it is not stored in plain text anywhere. Retrieve it from the Terraform state:

```bash
cd infrastructure/terraform/environments/production
terraform output -raw rds_endpoint
```

**RDS Endpoint Result**:
pilot-production.xxx.us-east-1.rds.amazonaws.com

> **AWS credentials**: Your `~/.aws/config` has only a `[default]` profile (IAM user `arn:aws:iam::000000000000:user/pilot-admin`, region `us-east-1`). No `--profile` flag is needed — the AWS CLI and Terraform both pick up `default` automatically.

It will look like:
```
pilot-production.cxxxxxxxxxx.us-east-1.rds.amazonaws.com
```

Save this value — you need it in Step 3.

> **Terraform state is remote** (S3 + DynamoDB lock). No `terraform apply` is needed — `output` reads from existing state only.

---

## Step 2 — Fetch the DB Password

The production password is stored in **AWS Secrets Manager** under `pilot/prod/db` (defined in [`infrastructure/terraform/modules/security/main.tf`](../../infrastructure/terraform/modules/security/main.tf)). Your AWS CLI `default` profile is used automatically — no `--profile` flag needed:

```bash
aws secretsmanager get-secret-value \
  --secret-id pilot/prod/db \
  --query SecretString \
  --output text \
  --region us-east-1
```

**Secret Response**:
{
  "dbname": "pilot_prod",
  "host": "pilot-production.xxx.us-east-1.rds.amazonaws.com",
  "password": "REDACTED_DB_PASSWORD",
  "port": 5432,
  "url": "postgresql://pilot_user:REDACTED_DB_PASSWORD@pilot-production.xxx.us-east-1.rds.amazonaws.com:5432/pilot_prod",
  "username": "pilot_user"
}

The output is a JSON string. The `password` field is what you need:

```json
{
  "username": "pilot_user",
  "password": "<your-password-here>",
  "host": "pilot-production.cxxxxxxxxxx.us-east-1.rds.amazonaws.com",
  "port": 5432,
  "dbname": "pilot_prod",
  "url": "postgresql://pilot_user:<password>@<host>:5432/pilot_prod"
}
```

Copy the `password` value — you need it in Step 4.

---

## Step 3 — Start the SSH Tunnel

Open a terminal and run (replace `<RDS_ENDPOINT>` with the value from Step 1):

```bash
ssh -L 5433:<RDS_ENDPOINT>:5432 pilot-bastion -N
```

**Using RDS Endpoint**:
```bash
ssh -L 5433:pilot-production.xxx.us-east-1.rds.amazonaws.com:5432 pilot-bastion -N
```

**Flags explained:**
- `-L 5433:<RDS_ENDPOINT>:5432` → forward your local port `5433` through the bastion to the RDS private endpoint on port `5432`
- `-N` → no remote command; keep the tunnel open and don't drop to a shell

The terminal will appear to hang — **that is correct**. The tunnel is active as long as this command is running. Leave this terminal open while you use VS Code.

> **Verify the tunnel is active before connecting:**
> ```bash
> lsof -i :5433
> # Should show: ssh ... localhost:5433 (LISTEN)
> ```

---

## Step 4 — Add the PROD Connection in VS Code

1. Open the **PostgreSQL Explorer** sidebar (elephant icon, or via Command Palette: `PostgreSQL: Add Connection`)
2. Click the **+** (Add Connection) button
3. Fill in the connection form:

| Field | Value |
|---|---|
| **Host** | `localhost` |
| **Port** | `5433` |
| **Database** | `pilot_prod` |
| **Username** | `pilot_user` |
| **Password** | *(value from Step 2)* |
| **SSL** | `Disable` *(SSL terminates at the bastion tunnel; not needed on localhost)* |
| **Connection Name** | `pilot_prod (via tunnel)` |

4. Click **Connect**

You should see the `pilot_prod` database appear in the explorer tree with all tables visible.

---

## Step 5 — Closing the Tunnel

When done, close the tunnel by pressing `Ctrl+C` in the terminal running the `ssh -L` command, or run this from any terminal:

```bash
pkill -f "ssh -L 5433" && echo "Tunnel closed" || echo "No tunnel was running"
```

> **Why not `kill $(pgrep ...)`?** If no tunnel is running, `pgrep` returns nothing and `kill` errors with `not enough arguments`. [`pkill`](https://man7.org/linux/man-pages/man1/pkill.1.html) handles the "no process found" case silently.

The VS Code extension will show a disconnected state — that is expected. The PROD connection **requires the tunnel to be running** each session.

---

## One-Liner: Full Session Startup

Combine Steps 1–3 into a single copy-paste block for fast session starts:

```bash
# From the project root — reads Terraform sensitive output then opens tunnel
RDS_ENDPOINT=$(cd infrastructure/terraform/environments/production && terraform output -raw rds_endpoint)

ssh -L 5433:$RDS_ENDPOINT:5432 pilot-bastion -N
# Leave this terminal open → switch to VS Code → connect
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `ssh: connect to host 203.0.113.12 port 22: Connection refused` | Bastion is stopped | Start bastion: `aws ec2 start-instances --instance-ids <BASTION_ID> --region us-east-1` |
| `Permission denied (publickey)` | Wrong key or key not loaded | Run `ssh-add ~/.ssh/pilot_admin_ed25519` first |
| `bind: Address already in use` on port 5433 | Previous tunnel not closed | `kill $(pgrep -f "ssh -L 5433")` then retry |
| `Connection refused` from VS Code on `localhost:5433` | Tunnel not started yet | Run Step 3 first; verify with `lsof -i :5433` |
| `FATAL: password authentication failed` | Stale/wrong password copied | Re-fetch from Secrets Manager (Step 2) |
| `Your IP is not allowed` | IP changed (backup ISP DHCP) | Update bastion SG: see [aws-ops-runbook.md §10.6](aws-ops-runbook.md) |
| `No value for output 'rds_endpoint'` | Terraform state not initialized | Run `terraform init` in `infrastructure/terraform/environments/production/` first |
| `Error: AccessDeniedException` on Secrets Manager | Expired or missing credentials | Run `aws sts get-caller-identity` — if it fails, re-run `aws configure` to re-enter your access key/secret |

---

## Reference

| Item | Value / Location |
|---|---|
| **Bastion Elastic IP** | `203.0.113.12` (never changes) |
| **SSH key** | `~/.ssh/pilot_admin_ed25519` |
| **SSH config alias** | `pilot-bastion` (in `~/.ssh/config`) |
| **AWS CLI profile** | `default` — your `~/.aws/config` has one profile; IAM user: `pilot-admin`; no `--profile` flag needed |
| **DB name** | `pilot_prod` |
| **DB user** | `pilot_user` |
| **RDS Terraform identifier** | `pilot-production` |
| **Secret name** | `pilot/prod/db` (AWS Secrets Manager, `us-east-1`) |
| **Secret defined in** | [`infrastructure/terraform/modules/security/main.tf`](../../infrastructure/terraform/modules/security/main.tf) |
| **Terraform env** | `infrastructure/terraform/environments/production/` |
| **Full runbook** | [`dev-docs/devops/aws-ops-runbook.md §10.7`](aws-ops-runbook.md) |
| **Infrastructure reference** | [`dev-docs/devops/aws-infrastructure-as-built.md §15`](aws-infrastructure-as-built.md) |
