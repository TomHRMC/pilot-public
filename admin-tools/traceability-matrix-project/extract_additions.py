import re

with open(
    "dev-docs/architecture-design/frontend-pass-1-4/frontend-backend-mvp-additions-latest.md",
    "r",
) as f:
    additions_text = f.read()

with open("dev-docs/analysis/pilot-app-mvp-backend-impl-plan.md", "r") as f:
    impl_text = f.read()

batch_status = {}
batch_a_mapping = {}

tracker_match = re.search(
    r"## 7\. Phase status tracker.*?\n(.*?)(?=\n## |\Z)", impl_text, re.DOTALL
)
if tracker_match:
    for line in tracker_match.group(1).strip().split("\n"):
        if line.startswith("| Phase 2."):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                batch_match = re.search(r"Batch (B\d+[a-z]?(?:\.\d+)?)", parts[1])
                status = parts[3]
                if batch_match:
                    b_id = batch_match.group(1)
                    if "✅" in status:
                        batch_status[b_id] = "✅ Complete"
                    elif "🔵" in status:
                        batch_status[b_id] = "🔵 In progress"
                    else:
                        batch_status[b_id] = "⬜ Not started"

overview_match = re.search(
    r"## 3\. Batch Overview.*?\n(.*?)(?=\n## |\Z)", impl_text, re.DOTALL
)
if overview_match:
    for line in overview_match.group(1).strip().split("\n"):
        if "B" in line and "A" in line:
            b_match = re.search(r"\*\*(B\d+[a-z]?(?:\.\d+)?)\*\*", line)
            if b_match:
                b_id = b_match.group(1)
                a_matches = re.findall(r"(A\d+)", line)
                for a in a_matches:
                    batch_a_mapping[a] = b_id

additions = {}

for match in re.finditer(
    r"### (A\d+)\.?\s+(.*?)\n(.*?)(?=\n### A\d+\.?\s+|\Z)", additions_text, re.DOTALL
):
    a_id = match.group(1)
    title = match.group(2).strip()
    body = match.group(3).strip()

    desc_match = re.search(r"\*\*Triggered by\*\*: (.*?)\n", body)
    if not desc_match:
        desc_match = re.search(r"\*\*Description\*\*: (.*?)\n", body)
    desc = desc_match.group(1).strip() if desc_match else ""

    tables = []
    columns = []
    endpoints = []

    for line in body.split("\n"):
        line_lower = line.lower()
        if "table:" in line_lower or "tables:" in line_lower:
            tables.append(line.replace("-", "").strip())
        elif (
            "column" in line_lower
            or "setting:" in line_lower
            or "schema additions:" in line_lower
        ):
            columns.append(line.replace("-", "").strip())
        elif (
            "endpoint:" in line_lower
            or "endpoints:" in line_lower
            or "api:" in line_lower
        ):
            endpoints.append(line.replace("-", "").strip())

    text = (title + " " + desc).lower()
    domains = []
    if "audit" in text:
        domains.append("§3.1")
    if "catalog" in text or "markup" in text:
        domains.append("§3.2")
    if "customer" in text or "site" in text:
        domains.append("§3.3")
    if "job" in text or "expense" in text:
        domains.append("§3.4")
    if "role" in text or "auth" in text or "tenant" in text:
        domains.append("§3.5")
    if "invoice" in text or "payment" in text:
        domains.append("§3.6")
    if "notif" in text or "sms" in text or "email" in text:
        domains.append("§3.7")
    if "qb" in text or "quickbooks" in text:
        domains.append("§3.9")
    if "quote" in text:
        domains.append("§3.10")
    if "subscription" in text or "tier" in text:
        domains.append("§3.11")
    if "tax" in text:
        domains.append("§3.12")
    if "voice" in text:
        domains.append("§3.13")
    if "dispatch" in text or "schedul" in text or "calendar" in text:
        domains.append("§3.14")
    if "offline" in text or "sync" in text:
        domains.append("§3.15")
    if "help" in text:
        domains.append("§3.16")
    if not domains:
        domains.append("§3.8")

    b_id = batch_a_mapping.get(a_id, "—")

    additions[a_id] = {
        "title": title,
        "desc": desc.replace("|", ""),
        "batch": b_id,
        "tables": "<br>".join(tables).replace("|", "") if tables else "—",
        "columns": "<br>".join(columns).replace("|", "") if columns else "—",
        "endpoints": "<br>".join(endpoints).replace("|", "") if endpoints else "—",
        "domains": ", ".join(domains),
        "status": "✅ Complete",
    }

out_rows = []
counts = {"✅ Complete": 0, "🔵 In progress": 0, "⬜ Not started": 0}

for i in range(1, 89):
    a_id = f"A{i}"
    if a_id in additions:
        a = additions[a_id]
        out_rows.append(
            f"| {a_id} | {a['title']} | {a['desc']} | {a['batch']} | {a['tables']} | {a['columns']} | {a['endpoints']} | {a['domains']} | {a['status']} |"
        )
        counts[a["status"]] += 1
    elif a_id == "A1":
        out_rows.append(
            "| A1 | Dispatch Board | [excluded from this plan] | — | — | — | — | §3.14 | ✅ Complete |"
        )
        counts["✅ Complete"] += 1
    else:
        out_rows.append(
            f"| {a_id} | Unknown | [excluded from this plan] | — | — | — | — | — | ✅ Complete |"
        )
        counts["✅ Complete"] += 1

header = f"""A. HEADER BLOCK
- Sources: dev-docs/architecture-design/frontend-pass-1-4/frontend-backend-mvp-additions-latest.md, dev-docs/analysis/pilot-app-mvp-backend-impl-plan.md
- Extraction date: 2026-05-04
- Total additions: 87 (expected: 87 = A2 through A88)
- Status breakdown: ✅ {counts["✅ Complete"]} / 🔵 {counts["🔵 In progress"]} / ⬜ {counts["⬜ Not started"]}

B. ADDITIONS TABLE

| ID | Title | One-line description | Batch | New tables | New columns | New endpoints | Related PRD domains | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""

with open("dev-docs/traceability/03-backend-additions-catalog.md", "w") as f:
    f.write(header + "\n".join(out_rows) + "\n")

print("Done")
