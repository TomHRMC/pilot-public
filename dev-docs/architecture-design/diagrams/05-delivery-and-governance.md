# Delivery and Governance — how a change gets from idea to a deployed AWS environment

*How work is designed, built, checked and shipped: one human architect directing specialized AI agents, behind a set of hard gates. Drawn from `METHOD.md`, `.roomodes`, the ADR log, `backend/schema_manager.py`, `admin-tools/` and `.github/workflows/`. Solid = built. Dashed orange = enterprise path (designed for, not built). See the [diagram index](README.md) for the legend and sources.*

## 1. Making a change — the gated workflow

```mermaid
flowchart TB
  human(["<b>Architect / owner</b><br/>one human · reviews every output<br/>owns the hard-to-reverse calls"])

  subgraph decide["Decide"]
    direction LR
    adr["<b>ADR log</b><br/>21 decisions with options considered<br/>sole living traceability doc (ADR-0009)"]
    spec["<b>Batch design spec</b><br/>Input Read Summary:<br/>PRD → design → generated sources"]
  end

  agents["<b>Specialized AI agents</b> · 12 roles<br/>architect · orchestrator · python · react · QA · devops<br/>integrations · voice AI · electrical domain · 3 UI designers<br/>each must read its own rules directory first<br/>work happens on a feature/* branch per batch"]

  subgraph gates["Gates every batch must pass"]
    direction LR
    base["<b>Regression baseline</b><br/>captured before any file is touched<br/>report: baseline → new, zero regressions"]
    schema["<b>Schema integrity</b><br/>Golden Master JSON changed only<br/>through schema_manager.py<br/>DDL-only migrations (ADR-0016)"]
    diff["<b>Schema-diff gate</b><br/>live DB vs master must reconcile<br/>backup_and_diff_schema.sh"]
    contract["<b>API contract</b><br/>openapi.json → generated<br/>TypeScript types (ADR-0007)<br/>the intended source of FE types"]
  end

  subgraph quality["Test depth"]
    direction LR
    unit["<b>pytest</b><br/>unit + integration<br/>isolation · audit · idempotency suites"]
    mut["<b>Mutation testing</b><br/>Cosmic Ray · 4 tiers<br/>money · tenant isolation ·<br/>state machines · voice + integrations"]
    e2e["<b>End-to-end</b><br/>5 critical paths (pytest)<br/>+ Playwright browser tests<br/>vendors mocked"]
  end

  close["<b>Closeout</b><br/>done = code + migration + master JSON<br/>+ docs + trackers, on a fixed template"]
  merge(["<b>Merge to dev</b><br/>only when the batch is fully tested"])
  promote(["<b>Promote by pull request</b><br/>dev → qa · qa deploys to the one AWS environment<br/>(demo and prod branches defined, not used)"])

  human --> adr --> spec --> agents
  agents --> base & schema & contract
  schema --> diff
  base & diff & contract --> unit
  unit --> mut & e2e
  unit --> close
  human -- "runs migrations, diffs and tests<br/>confirms at each gate" --> gates
  close --> merge --> promote
```

## 2. Shipping it — the deploy pipeline

```mermaid
flowchart LR
  push(["<b>push to qa</b><br/>release branch for the one AWS<br/>environment (QA + production candidate)"])

  subgraph checks["Checks"]
    direction TB
    test["<b>Backend unit tests</b><br/>pytest -m unit · a failure stops the release"]
    scan["<b>Secret scan</b><br/>Trivy · source tree<br/>fails on HIGH / CRITICAL"]
  end

  oidc["<b>AWS via OIDC</b><br/>short-lived role credentials<br/>no stored AWS keys"]

  subgraph backend["Backend"]
    direction TB
    build["<b>Build once</b><br/>one image → api · worker · beat<br/>tagged with the commit SHA → ECR"]
    mig["<b>Migrate</b><br/>alembic upgrade head<br/>one-off Fargate task, private subnet<br/>non-zero exit stops the deploy"]
    dep["<b>Deploy</b><br/>rolling update · api, worker, beat<br/>wait for stable · circuit-breaker rollback"]
  end

  subgraph frontend["Frontend"]
    direction TB
    web["<b>Web dashboard</b><br/>Docker → ECR → ECS"]
    mkt["<b>Marketing site</b><br/>static export → S3<br/>assets cached 1 yr · HTML no-cache<br/>CloudFront invalidation"]
  end

  smoke["<b>Post-deploy checks</b><br/>marketing up · API /health<br/>prod /test routes must return 403<br/>any failure fails the run"]

  push --> test & scan
  test & scan --> oidc
  oidc --> build --> mig --> dep --> smoke
  oidc --> web
  oidc --> mkt --> smoke

  gate["Lint, type-check and<br/>coverage gates in CI<br/><i>ruff and Prettier config exist</i>"]:::path
  deps["Dependency + image scanning<br/>SBOM · signed images"]:::path
  stage["<b>Separate QA stack</b><br/>deployed once from the same Terraform,<br/>tested, then torn down to save cost"]
  bg["CodeDeploy blue/green<br/>one-click rollback<br/><i>green target group staged;<br/>kill-switch input declared</i>"]:::path
  nightly["Nightly E2E on a schedule<br/><i>workflow built; runs on demand</i>"]:::path

  test -.-> gate
  scan -.-> deps
  build --> stage
  dep -.-> bg
  smoke -.-> nightly

  classDef path stroke:#c77700,stroke-width:2px,stroke-dasharray:6 4;
  linkStyle 11,12,14,15 stroke:#c77700,stroke-width:2px;
```

## What this shows

- **Decisions are written down before they're built.** Every architecture decision is in the [ADR log](../pilot-adr-log.md) with the options that were rejected and why. Designs cite their inputs, so a reviewer can trace a feature back to the requirement.
- **The agents have no latitude on the dangerous parts.** The schema changes only through one tool, migrations carry structure only (all data comes from environment-aware seed scripts), the frontend has generated types from the API contract as its intended source (some hand-written interfaces remain; Known Limitations #8), and no batch closes without a before-and-after test count. The human runs the migrations, schema diffs and test suites at each gate.
- **Tests aim at what would hurt most.** Mutation testing is tiered by blast radius: financial correctness first, then tenant isolation, then workflow state machines, then voice and integrations.
- **AWS access from CI is keyless.** CI assumes an AWS role through GitHub OIDC; there are no long-lived AWS keys in the repo or the CI settings.
- **Manual deploys where they paid off.** For most of the build, deploys were run by hand so that interim builds, single components or one integration at a time could be tested in AWS. The pipeline handles full releases from the `qa` branch.
- **One artifact, three services.** The API, worker and scheduler run the same image built once per commit, so they can't drift apart, and the migration runs inside the VPC before any new code takes traffic.

## Enterprise path shown here

| Upgrade | Why it's next | Starting point already in place |
|---|---|---|
| Lint, type-check and coverage gates in CI | Style, typing and coverage regressions stop the release, not just failing tests | Unit tests and post-deploy checks already block; ruff and Prettier configured; coverage measured (76% backend) |
| Dependency and image scanning, SBOM, signed images | Supply-chain assurance | Trivy already in the pipeline for secrets |
| Standing separate QA environment | Prove a release in a production-like environment before it would reach customers | QA infrastructure already deployed and tested once from the same Terraform, then torn down to save cost; environment profiles for dev, e2e, QA and prod ([ADR-0016](../pilot-adr-log.md)) |
| CodeDeploy blue/green with one-click rollback | Instant cut-over and rollback | Green target group provisioned; kill-switch input declared in the workflow |
| Scheduled nightly E2E | Catch regressions in the critical paths every day | Two-tier E2E workflow built; runs on demand |

## Sources

`METHOD.md` · `.roomodes` · [ADR log](../pilot-adr-log.md) (ADR-0007, -0009, -0016) · `backend/schema_manager.py` · `backend/README-cosmic-ray.md` · `admin-tools/backup_and_diff_schema.sh` · `.github/workflows/deploy-production.yml` · `.github/workflows/e2e-nightly.yml` · `frontend/.husky/pre-commit`
