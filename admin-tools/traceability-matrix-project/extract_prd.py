import re

with open("dev-docs/product-requirements/mvp-prd.md", "r") as f:
    prd_text = f.read()

version = "3.1 (final)"
date = "Apr 30, 2026"

domain_pattern = re.compile(
    r"### 3\.(\d+) (.*?)\n\n.*?\| Feature \| Description \|\n\| :--- \| :--- \|\n(.*?)(?=\n\n---|\n\n###|$)",
    re.DOTALL,
)
domains = domain_pattern.findall(prd_text)

per_domain_counts = {}
domain_sections = []
total = 0

import string


def get_entities(name, desc):
    text = name + " " + desc
    words = text.split()
    entities = []
    stopwords = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "by",
        "of",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "can",
        "could",
        "should",
        "would",
        "may",
        "might",
        "must",
        "will",
        "shall",
        "that",
        "this",
        "these",
        "those",
    }
    for w in words:
        w = w.strip(string.punctuation).lower()
        if w and w not in stopwords and len(w) > 3:
            if w not in entities:
                entities.append(w)
    return ", ".join(entities[:5])


for num, title, table_text in domains:
    rows = table_text.strip().split("\n")
    features = []
    for r in rows:
        if not r.strip():
            continue
        parts = [p.strip() for p in r.split("|")]
        if len(parts) >= 3:
            name = parts[1].replace("**", "").strip()
            desc = parts[2].strip()
            features.append((name, desc))

    if num == "16":
        # Let's double check if 16 got truncated
        pass

    per_domain_counts[f"§3.{num}"] = len(features)
    total += len(features)

    sec_text = f"## §3.{num} {title}\n\n"
    sec_text += (
        "| ID | Feature name | One-line description | Implied entities/concepts |\n"
    )
    sec_text += "| :--- | :--- | :--- | :--- |\n"

    for i, (name, desc) in enumerate(features, 1):
        desc_compress = desc.replace("\n", " ").replace("|", ",")
        # simple compression: remove some fluff
        desc_compress = re.sub(r"\s+", " ", desc_compress)
        implied = get_entities(name, desc)

        sec_text += f"| PRD-§3.{num}-F{i} | {name} | {desc_compress} | {implied} |\n"

    domain_sections.append(sec_text)

header = (
    f"""A. HEADER BLOCK
- Source: dev-docs/product-requirements/mvp-prd.md §3.1–§3.16 (PRD v{version}, {date})
- Extraction date: 2026-05-04
- Total features: {total}
- Per-domain row counts: """
    + " | ".join([f"{k}: {v}" for k, v in per_domain_counts.items()])
    + "\n\n"
)

header += "B. SIXTEEN PER-DOMAIN SECTIONS\n\n"

with open("dev-docs/traceability/01-prd-requirements-catalog.md", "w") as f:
    f.write(header + "\n\n".join(domain_sections))

print(f"Total features: {total}")
