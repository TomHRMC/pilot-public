import re

with open("dev-docs/architecture-design/mvp-arch.md", "r") as f:
    arch_text = f.read()

# Match the version and date
version_match = re.search(r"\*\*Version\*\*: (.*?)\n", arch_text)
date_match = re.search(r"\*\*Last Updated:\*\* (.*?)\n", arch_text)
version = version_match.group(1).split(" ")[0] if version_match else "5"
date = date_match.group(1).strip() if date_match else "April 30, 2026"

# Regex to find headings (### 1.1, #### 1.1.1, etc.)
# We'll collect all headings and their text
headings = []
for match in re.finditer(
    r"^(#{3,5})\s+(\d+\.\d+(?:\.\d+)?)\s+(.*?)\n(.*?)(?=\n#{2,} |\Z)",
    arch_text,
    re.MULTILINE | re.DOTALL,
):
    level = len(match.group(1))
    num = match.group(2)
    title = match.group(3).strip()
    body = match.group(4).strip()
    headings.append((num, title, body))

# We want leaf-level sections. A section is a leaf if no other section starts with its number + "."
leaf_sections = []
for i, (num, title, body) in enumerate(headings):
    # Check if there's any section that starts with num + "."
    is_leaf = True
    for j in range(i + 1, len(headings)):
        next_num = headings[j][0]
        if next_num.startswith(num + "."):
            is_leaf = False
            break
        elif not next_num.startswith(num.split(".")[0] + "."):
            # different top-level, we can stop checking
            break

    if is_leaf:
        leaf_sections.append((num, title, body))

# Now we generate the table rows


def summarize(title, body):
    # simple summarizer for the decision statement
    # try to get the first sentence or two
    body_clean = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body_clean = re.sub(r"\|.*?\|", "", body_clean)
    body_clean = re.sub(r"[#\*\-\>]", "", body_clean)
    body_clean = " ".join(body_clean.split())
    sentences = re.split(r"(?<=[.!?])\s+", body_clean)
    if sentences and sentences[0]:
        decision = sentences[0]
        if len(sentences) > 1 and len(decision) < 100:
            decision += " " + sentences[1]
    else:
        decision = "[descriptive only]"

    # if it doesn't sound like a decision or is too short, maybe add descriptive only
    if len(decision.strip()) < 10 and not decision.startswith("["):
        decision = "[descriptive only]"

    return decision[:300].strip()


def get_components(body):
    # extract things that look like tables, services, modules
    # `table_name`, `service.py`, FastAPI, Celery
    components = []
    codes = re.findall(r"`([a-zA-Z0-9_\.]+)`", body)
    for c in codes:
        if c not in components and len(c) > 2:
            components.append(c)

    # Some hardcoded ones
    if "FastAPI" in body and "FastAPI" not in components:
        components.append("FastAPI")
    if "Celery" in body and "Celery" not in components:
        components.append("Celery")
    if "PostgreSQL" in body and "PostgreSQL" not in components:
        components.append("PostgreSQL")
    if "Redis" in body and "Redis" not in components:
        components.append("Redis")
    if "Stripe" in body and "Stripe" not in components:
        components.append("Stripe")
    if "Telnyx" in body and "Telnyx" not in components:
        components.append("Telnyx")

    return ", ".join(components[:6])


def get_domains(num, title, body):
    domains = []
    # simple keyword mapping
    text = (title + " " + body).lower()
    if "audit" in text or "compliance" in text:
        domains.append("§3.1")
    if "catalog" in text or "pric" in text or "markup" in text:
        domains.append("§3.2")
    if "customer" in text or "crm" in text or "site" in text:
        domains.append("§3.3")
    if "job" in text or "expense" in text or "time" in text or "tech" in text:
        domains.append("§3.4")
    if (
        "auth" in text
        or "tenant" in text
        or "rbac" in text
        or "cognito" in text
        or "mfa" in text
    ):
        domains.append("§3.5")
    if "invoice" in text or "bill" in text or "payment" in text:
        domains.append("§3.6")
    if "notif" in text or "sms" in text or "email" in text or "comm" in text:
        domains.append("§3.7")
    if "infra" in text or "aws" in text or "vpc" in text or "deploy" in text:
        domains.append("§3.8")
    if "quickbooks" in text or "qbo" in text:
        domains.append("§3.9")
    if "quote" in text or "sales" in text or "discount" in text:
        domains.append("§3.10")
    if "subscription" in text or "tier" in text or "stripe" in text:
        domains.append("§3.11")
    if "tax" in text:
        domains.append("§3.12")
    if "voice" in text or "whisper" in text or "llama" in text or "intent" in text:
        domains.append("§3.13")
    if "schedul" in text or "dispatch" in text or "calendar" in text:
        domains.append("§3.14")
    if "offline" in text or "sync" in text:
        domains.append("§3.15")
    if "help" in text or "support" in text or "rag" in text:
        domains.append("§3.16")

    if not domains:
        domains.append("§3.8")  # default to platform infra

    # dedup and sort
    domains = sorted(list(set(domains)), key=lambda x: float(x.replace("§", "")))
    return ", ".join(domains)


out_rows = []
for num, title, body in leaf_sections:
    decision = summarize(title, body)
    components = get_components(body)
    domains = get_domains(num, title, body)
    out_rows.append(
        f"| ARCH-§{num} | {title} | {decision} | {components} | {domains} |"
    )

header = f"""A. HEADER BLOCK
- Source: dev-docs/architecture-design/mvp-arch.md (v{version}, {date})
- Extraction date: 2026-05-04
- Total decisions cataloged: {len(out_rows)}

B. DECISIONS TABLE

| ID | Section title | Decision / pattern statement | Affected components | Related PRD domains |
| :--- | :--- | :--- | :--- | :--- |
"""

with open("dev-docs/traceability/02-arch-decisions-catalog.md", "w") as f:
    f.write(header + "\n".join(out_rows) + "\n")

print(f"Total decisions: {len(out_rows)}")
