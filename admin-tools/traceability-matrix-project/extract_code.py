import glob
import json
import os
import re
import urllib.request
from datetime import datetime

# Fetch OpenAPI
openapi = None
try:
    req = urllib.request.Request("http://localhost:8000/openapi.json")
    with urllib.request.urlopen(req) as response:
        openapi = json.loads(response.read().decode("utf-8"))
except Exception as e:
    print(
        f"Error fetching OpenAPI: {e}. Please ensure the FastAPI server is running at http://localhost:8000"
    )
    exit(1)

findings = []


def add_finding(severity, title, desc, affected):
    # Find next finding ID
    try:
        with open("dev-docs/traceability/findings-ledger.md", "r") as f:
            ledger = f.read()
            matches = re.findall(r"FIND-(\d+)", ledger)
            next_id = max([int(m) for m in matches] + [0]) + 1
    except:
        next_id = 1
    fid = f"FIND-{next_id:03d}"
    findings.append(
        f"| {fid} | Phase 1.5 | {severity} | 1.5 | {title} | {desc} | {affected} | REMEDIATION_PLANNED | OPEN |"
    )

    # Actually just append it right away for simplicity
    with open("dev-docs/traceability/findings-ledger.md", "a") as f:
        f.write(
            f"\n| {fid} | Phase 1.5 | {severity} | 1.5 | {title} | {desc} | {affected} |  | OPEN |"
        )


# 1. API Endpoints
endpoints = []
for path, methods in openapi.get("paths", {}).items():
    for method, details in methods.items():
        if method.lower() not in ["get", "post", "put", "patch", "delete"]:
            continue
        op_id = details.get("operationId", "unknown")

        req_schema = "—"
        if "requestBody" in details and "content" in details["requestBody"]:
            for content_type, cdata in details["requestBody"]["content"].items():
                if "schema" in cdata and "$ref" in cdata["schema"]:
                    ref = cdata["schema"]["$ref"].split("/")[-1]
                    req_schema = f"SCM-?/{ref}"  # Needs mapping

        res_schema = "—"
        if "responses" in details and "200" in details["responses"]:
            resp = details["responses"]["200"]
            if "content" in resp:
                for content_type, cdata in resp["content"].items():
                    if "schema" in cdata and "$ref" in cdata["schema"]:
                        ref = cdata["schema"]["$ref"].split("/")[-1]
                        res_schema = f"SCM-?/{ref}"

        endpoints.append(
            {
                "path": path,
                "method": method.upper(),
                "op_id": op_id,
                "req_schema": req_schema,
                "res_schema": res_schema,
            }
        )

# Parse route files for RBAC
route_files = glob.glob("backend/api/routes/**/*.py", recursive=True)
route_rbac = {}
for rf in route_files:
    with open(rf, "r") as f:
        content = f.read()
        # Look for @router.get("/path") ... def handler(... Depends(require_permission("xyz")))
        # It's hard to parse perfectly without AST, but regex works reasonably well
        matches = re.finditer(
            r"@router\.(get|post|put|patch|delete)\(\"(.*?)\".*?def (\w+)\(.*?(?:require_permission\([\"'](.*?)[\"']\))?",
            content,
            re.DOTALL,
        )
        for m in matches:
            method = m.group(1).upper()
            r_path = m.group(2)
            handler = m.group(3)
            perm = m.group(4) if m.group(4) else "[unguarded]"
            route_rbac[f"{method}-{r_path}"] = {
                "handler": handler,
                "perm": perm,
                "file": os.path.basename(rf),
            }

# Match OpenAPI with route_rbac
final_endpoints = []
for ep in endpoints:
    # try to match path. OpenAPI might have /v1/quotes/{id}, code might have /{id} with router prefix
    # So we match by op_id or just guess. For now, let's match by op_id if possible
    # Actually, fastAPI operation_id is usually handler name
    found = False
    for key, data in route_rbac.items():
        if data["handler"] == ep["op_id"]:
            ep["handler"] = data["handler"]
            ep["perm"] = data["perm"]
            ep["file"] = data["file"]
            found = True
            break

    if not found:
        ep["handler"] = ep["op_id"]
        ep["perm"] = "[unguarded]"
        ep["file"] = "unknown"

    # Check tenant scoped but unguarded
    if ("{tenant_id}" in ep["path"] or "tenant" in ep["path"]) and ep[
        "perm"
    ] == "[unguarded]":
        add_finding(
            "S1 Critical",
            "Unguarded tenant endpoint",
            f"Endpoint {ep['method']} {ep['path']} lacks RBAC guard",
            f"EP-{ep['method']}-{ep['path']}",
        )

    final_endpoints.append(ep)

# 2. Pydantic Schemas
schemas = []
for sf in glob.glob("backend/api/schemas/**/*.py", recursive=True):
    with open(sf, "r") as f:
        content = f.read()
        classes = re.findall(
            r"class ([a-zA-Z0-9_]+)\(.*?(?:BaseModel|SQLModel)", content
        )
        for c in classes:
            if c.startswith("_"):
                continue
            module = os.path.basename(sf).replace(".py", "")
            schemas.append(
                {
                    "id": f"SCM-{module}.{c}",
                    "class": c,
                    "purpose": "DTO / Request / Response",
                    "file": os.path.basename(sf),
                }
            )

# 3. ORM Models
models = []
for mf in glob.glob("backend/app/models/**/*.py", recursive=True):
    with open(mf, "r") as f:
        content = f.read()
        classes = re.findall(r"class ([a-zA-Z0-9_]+)\(.*?(?:SQLModel|Base)", content)
        for c in classes:
            if c.startswith("_"):
                continue
            module = os.path.basename(mf).replace(".py", "")
            # try to extract table name
            tmatch = re.search(
                f"class {c}.*?__tablename__\s*=\s*['\"](.*?)['\"]", content, re.DOTALL
            )
            table = tmatch.group(1) if tmatch else c.lower()
            models.append(
                {
                    "id": f"MOD-{module}.{c}",
                    "class": c,
                    "table": table,
                    "file": os.path.basename(mf),
                }
            )

# 4. Services
services = []
for sf in glob.glob("backend/services/**/*.py", recursive=True):
    with open(sf, "r") as f:
        content = f.read()
        funcs = re.findall(
            r"async def ([a-zA-Z0-9_]+)\(|def ([a-zA-Z0-9_]+)\(", content
        )
        for f1, f2 in funcs:
            func = f1 or f2
            if func.startswith("_"):
                continue
            module = os.path.basename(sf).replace(".py", "")
            services.append(
                {
                    "id": f"SVC-{module}.{func}",
                    "function": func,
                    "behavior": "Service function",
                    "file": os.path.basename(sf),
                }
            )

# 5. Tasks
tasks = []
for tf in glob.glob("backend/tasks/**/*.py", recursive=True):
    with open(tf, "r") as f:
        content = f.read()
        funcs = re.findall(
            r"@shared_task.*?\n(?:async )?def ([a-zA-Z0-9_]+)\(", content, re.DOTALL
        )
        for func in funcs:
            module = os.path.basename(tf).replace(".py", "")
            tasks.append(
                {
                    "id": f"TSK-{module}.{func}",
                    "task": func,
                    "purpose": "Background task",
                    "schedule": "Unknown",
                    "file": os.path.basename(tf),
                }
            )

# 6. Voice Intents
intents = []
try:
    with open("backend/services/voice_action_router.py", "r") as f:
        content = f.read()
        registry = re.search(r"INTENT_HANDLERS\s*=\s*\{(.*?)\}", content, re.DOTALL)
        if registry:
            items = re.findall(
                r"[\"'](.*?)[\"']\s*:\s*([a-zA-Z0-9_]+)", registry.group(1)
            )
            for intent, handler in items:
                intents.append(
                    {
                        "id": f"VI-{intent}",
                        "intent": intent,
                        "handler": handler,
                        "file": "voice_action_router.py",
                    }
                )
except Exception:
    pass

# Generate Markdown
out = []
out.append("A. HEADER BLOCK")
out.append(
    "- Sources: http://localhost:8000/openapi.json, backend/api/routes/, backend/api/schemas/, backend/app/models/, backend/services/, backend/tasks/"
)
out.append(f"- Extraction date: {datetime.now().strftime('%Y-%m-%d')}")
out.append(
    f"- Counts: {len(final_endpoints)} endpoints / {len(schemas)} schemas / {len(models)} models / {len(services)} services / {len(tasks)} tasks / {len(intents)} voice intents"
)
out.append("")

out.append("B. API ENDPOINTS")
guarded = len([e for e in final_endpoints if e["perm"] != "[unguarded]"])
tenant_unguarded = len(
    [
        e
        for e in final_endpoints
        if e["perm"] == "[unguarded]" and ("tenant" in e["path"])
    ]
)
out.append(f"- Total endpoints: {len(final_endpoints)}")
out.append(f"- Endpoints with RBAC guard: {guarded}")
out.append(f"- Tenant-scoped endpoints without RBAC guard: {tenant_unguarded}")
out.append("")
out.append(
    "| ID | Method | Path | OpenAPI operation_id | Handler | Auth | RBAC permission | Request schema | Response schema | File |"
)
out.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
for e in sorted(final_endpoints, key=lambda x: f"EP-{x['method']}-{x['path']}"):
    eid = f"EP-{e['method']}-{e['path']}"
    out.append(
        f"| {eid} | {e['method']} | {e['path']} | {e['op_id']} | {e['handler']} | JWT | {e['perm']} | {e['req_schema']} | {e['res_schema']} | {e['file']} |"
    )
out.append("")

out.append("C. PYDANTIC SCHEMAS")
out.append("| ID | Class | Purpose | File |")
out.append("| :--- | :--- | :--- | :--- |")
for s in sorted(schemas, key=lambda x: x["id"]):
    out.append(f"| {s['id']} | {s['class']} | {s['purpose']} | {s['file']} |")
out.append("")

out.append("D. ORM MODELS")
out.append("| ID | Class | Table | File |")
out.append("| :--- | :--- | :--- | :--- |")
for m in sorted(models, key=lambda x: x["id"]):
    out.append(f"| {m['id']} | {m['class']} | {m['table']} | {m['file']} |")
out.append("")

out.append("E. SERVICES")
out.append("| ID | Function | One-line behavior | File |")
out.append("| :--- | :--- | :--- | :--- |")
for s in sorted(services, key=lambda x: x["id"]):
    out.append(f"| {s['id']} | {s['function']} | {s['behavior']} | {s['file']} |")
out.append("")

out.append("F. CELERY TASKS")
out.append("| ID | Task | Purpose | Schedule | File |")
out.append("| :--- | :--- | :--- | :--- | :--- |")
for t in sorted(tasks, key=lambda x: x["id"]):
    out.append(
        f"| {t['id']} | {t['task']} | {t['purpose']} | {t['schedule']} | {t['file']} |"
    )
out.append("")

out.append("G. VOICE INTENTS")
out.append("| ID | Intent name | Handler | Source file |")
out.append("| :--- | :--- | :--- | :--- |")
for i in sorted(intents, key=lambda x: x["id"]):
    out.append(f"| {i['id']} | {i['intent']} | {i['handler']} | {i['file']} |")
out.append("")

with open("dev-docs/traceability/05-backend-code-catalog.md", "w") as f:
    f.write("\n".join(out))

print("Done")
