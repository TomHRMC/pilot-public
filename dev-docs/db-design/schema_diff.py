import argparse
import html as html_lib
import json
import re


def normalize_index_def(def_str):
    """Reduces an index definition to its pure structural core for comparison."""
    if not def_str:
        return ""

    # Aggressively strip the "CREATE INDEX name ON table" prefix if it exists
    # so full SQL strings perfectly match partial JSON strings.
    def_str = re.sub(
        r"(?i)^CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?[\w\".]+\s+ON\s+[\w\".]+\s*",
        "",
        def_str,
    )

    def_str = re.sub(r"(?i)\s*WITH\s*\([^)]*\)", "", def_str)
    def_str = re.sub(r"(?i)\s*TABLESPACE\s+[a-zA-Z0-9_]+", "", def_str)
    def_str = re.sub(r"(?i)USING\s+btree\s*", "", def_str)
    def_str = re.sub(r"(?i)public\.", "", def_str)
    def_str = re.sub(r"(?i)ASC", "", def_str)
    def_str = re.sub(r"(?i)NULLS\s+LAST", "", def_str)
    def_str = re.sub(r"(?i)NULLS\s+FIRST", "", def_str)

    def_str = re.sub(r'[\s"\'`]', "", def_str).lower()
    return def_str


def parse_json_schema(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    tables = {}
    functions = {}

    # -- Extract Functions --
    for func in data.get("functions", []):
        name = func.get("name")
        schema = func.get("schema", "public")
        # Handle cases where schema is already embedded in the name
        full_name = name if "." in name else f"{schema}.{name}"
        # Normalize whitespace for clean comparison
        def_str = re.sub(r"\s+", " ", func.get("definition", "")).strip()
        functions[full_name] = def_str

    # -- Extract Tables --
    def norm_cols(val):
        if isinstance(val, list):
            return ",".join(val).replace(" ", "")
        return str(val).replace(" ", "")

    def process_tables(table_dict, schema_name):
        for table_name, table_data in table_dict.items():
            full_name = f"{schema_name}.{table_name}"
            columns = list(table_data.get("columns", {}).keys())
            pks = table_data.get("primary_key", [])

            # --- FIXED: Handle both legacy arrays and advanced unique dictionaries ---
            uniques = set()
            for u in table_data.get("unique", []):
                if isinstance(u, list):
                    uniques.add(tuple(u))
                elif isinstance(u, dict):
                    uniques.add(tuple(u.get("columns", [])))

            indexes = {}
            for idx in table_data.get("indexes", []):
                idx_name = idx.get("name")
                idx_def = idx.get("definition", "")
                norm_def = normalize_index_def(idx_def)
                if norm_def:
                    indexes[norm_def] = {"name": idx_name, "raw": json.dumps(idx)}

            fks = []
            for fk in table_data.get("foreign_keys", []):
                # Handle both flat "ref_table" and nested "references" formats
                ref_t = fk.get("ref_table")
                ref_cols_raw = fk.get("ref_columns", "")

                if not ref_t and "references" in fk:
                    ref_t = fk["references"].get("table")
                    ref_cols_raw = fk["references"].get("columns", "")

                # Safeguard against entirely malformed FKs
                if not ref_t:
                    continue

                if "." not in ref_t:
                    ref_t = f"public.{ref_t}"

                cols = norm_cols(fk.get("columns", ""))
                ref_cols = norm_cols(ref_cols_raw)
                fks.append((cols, ref_t, ref_cols))

            triggers = {}
            for trig in table_data.get("triggers", []):
                trig_name = trig.get("name")
                if trig_name:
                    triggers[trig_name] = trig.get("definition", "")

            tables[full_name] = {
                "columns": set(columns),
                "pks": set(pks),
                "uniques": uniques,
                "indexes": indexes,
                "fks": set(fks),
                "triggers": triggers,
            }

    process_tables(data.get("tables", {}), "public")
    for schema_name, schema_data in data.get("schemas", {}).items():
        process_tables(schema_data.get("tables", {}), schema_name)

    return tables, functions


def parse_sql_schema(sql_file):
    with open(sql_file, "r", encoding="utf-8") as f:
        raw_sql = f.read()

    functions = {}

    # -- Extract Functions BEFORE stripping comments --
    func_pattern = re.compile(
        r"(CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+((?:[a-zA-Z0-9_]+\.)?[a-zA-Z0-9_]+)\s*\([^)]*\).*?(?:\$[a-zA-Z0-9_]*\$).*?(?:\$[a-zA-Z0-9_]*\$)[^;]*;)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in func_pattern.finditer(raw_sql):
        full_def = match.group(1)
        func_name = match.group(2).strip()
        if "." not in func_name:
            func_name = f"public.{func_name}"

        # Normalize whitespace
        def_str = re.sub(r"\s+", " ", full_def).strip()
        functions[func_name] = def_str

    # -- Now strip standard comments for table extraction --
    raw_sql = re.sub(r"--.*", "", raw_sql)
    tables = {}
    statements = raw_sql.split(";")

    for raw_stmt in statements:
        stmt = re.sub(r"\s+", " ", raw_stmt).strip()
        if not stmt:
            continue

        create_re = re.search(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?\s*\((.*)\)',
            stmt,
            re.IGNORECASE,
        )
        if create_re:
            schema = create_re.group(1) or "public"
            table = create_re.group(2)
            full_name = f"{schema}.{table}"

            if full_name not in tables:
                tables[full_name] = {
                    "columns": set(),
                    "pks": set(),
                    "uniques": set(),
                    "indexes": {},
                    "fks": set(),
                    "triggers": {},
                }

            for line in raw_stmt.split("\n"):
                line_stripped = line.strip()
                if (
                    not line_stripped
                    or line_stripped == "("
                    or line_stripped.upper().startswith("CREATE ")
                ):
                    continue

                # --- FIXED: Added (?:\s+NULLS\s+(?:NOT\s+)?DISTINCT)? to gracefully ignore Postgres 15 modifiers ---
                m = re.search(
                    r"(PRIMARY KEY|UNIQUE)(?:\s+NULLS\s+(?:NOT\s+)?DISTINCT)?\s*\(([^)]+)\)",
                    line_stripped,
                    re.IGNORECASE,
                )
                if m and not line_stripped.upper().startswith("ALTER"):
                    c_type = m.group(1).upper()
                    cols = [c.strip(" '\"") for c in m.group(2).split(",")]
                    if c_type == "PRIMARY KEY":
                        tables[full_name]["pks"].update(cols)
                    elif c_type == "UNIQUE":
                        tables[full_name]["uniques"].add(tuple(cols))
                    continue

                fk_m = re.search(
                    r'FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?\s*\(([^)]+)\)',
                    line_stripped,
                    re.IGNORECASE,
                )
                if fk_m:
                    cols = fk_m.group(1).replace(" ", "").replace('"', "")
                    ref_s = fk_m.group(2) or "public"
                    ref_t = fk_m.group(3)
                    ref_cols = fk_m.group(4).replace(" ", "").replace('"', "")
                    tables[full_name]["fks"].add((cols, f"{ref_s}.{ref_t}", ref_cols))
                    continue

                if (
                    line_stripped.startswith(")")
                    or line_stripped.upper().startswith("CONSTRAINT ")
                    or line_stripped.upper().startswith("CHECK ")
                    or line_stripped.upper().startswith("CHECK(")
                ):
                    continue
                parts = line_stripped.split()
                if parts:
                    col_name = parts[0].strip(",\"'()")
                    if col_name and col_name.upper() not in [
                        "CONSTRAINT",
                        "PRIMARY",
                        "UNIQUE",
                        "FOREIGN",
                        "CHECK",
                        "CREATE",
                        "TABLE",
                        "IF",
                    ]:
                        tables[full_name]["columns"].add(col_name)

        if stmt.upper().startswith("ALTER TABLE"):
            # --- FIXED: Added (?:\s+NULLS\s+(?:NOT\s+)?DISTINCT)? to ALTER TABLE regex ---
            alt_match = re.search(
                r'ALTER\s+TABLE\s+(?:ONLY\s+)?(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?\s+ADD\s+CONSTRAINT\s+"?[a-zA-Z0-9_]+"?\s+(PRIMARY KEY|UNIQUE)(?:\s+NULLS\s+(?:NOT\s+)?DISTINCT)?\s*\(([^)]+)\)',
                stmt,
                re.IGNORECASE,
            )
            if alt_match:
                schema = alt_match.group(1) or "public"
                table = alt_match.group(2)
                c_type = alt_match.group(3).upper()
                cols = [c.strip(" '\"") for c in alt_match.group(4).split(",")]
                full_name = f"{schema}.{table}"
                if full_name in tables:
                    if c_type == "PRIMARY KEY":
                        tables[full_name]["pks"].update(cols)
                    elif c_type == "UNIQUE":
                        tables[full_name]["uniques"].add(tuple(cols))

            fk_alt_match = re.search(
                r'ALTER\s+TABLE\s+(?:ONLY\s+)?(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?\s+ADD\s+CONSTRAINT\s+"?[a-zA-Z0-9_]+"?\s+FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?\s*\(([^)]+)\)',
                stmt,
                re.IGNORECASE,
            )

            excl_match = re.search(
                r'ALTER\s+TABLE\s+(?:ONLY\s+)?(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?\s+ADD\s+CONSTRAINT\s+"?([a-zA-Z0-9_]+)"?\s+EXCLUDE\s+(USING\s+.*)',
                stmt,
                re.IGNORECASE,
            )
            if excl_match:
                schema = excl_match.group(1) or "public"
                table = excl_match.group(2)
                idx_name = excl_match.group(3)
                remainder = excl_match.group(4)
                full_name = f"{schema}.{table}"
                if full_name in tables:
                    norm_def = normalize_index_def(remainder)
                    if norm_def:
                        tables[full_name]["indexes"][norm_def] = {
                            "name": idx_name,
                            "raw": stmt,
                        }

            if fk_alt_match:
                schema = fk_alt_match.group(1) or "public"
                table = fk_alt_match.group(2)
                cols = fk_alt_match.group(3).replace(" ", "").replace('"', "")
                ref_s = fk_alt_match.group(4) or "public"
                ref_t = fk_alt_match.group(5)
                ref_cols = fk_alt_match.group(6).replace(" ", "").replace('"', "")
                full_name = f"{schema}.{table}"
                if full_name in tables:
                    tables[full_name]["fks"].add((cols, f"{ref_s}.{ref_t}", ref_cols))

        idx_match = re.search(
            r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?"?([a-zA-Z0-9_]+)"?\s+ON\s+(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?\s+(.*)',
            stmt,
            re.IGNORECASE,
        )
        if idx_match:
            idx_name = idx_match.group(1)
            schema = idx_match.group(2) or "public"
            table = idx_match.group(3)

            # Use the FULL stmt string so the regex in normalize_index_def can do its job
            norm_def = normalize_index_def(stmt)

            full_name = f"{schema}.{table}"
            if full_name in tables and norm_def:
                tables[full_name]["indexes"][norm_def] = {"name": idx_name, "raw": stmt}

        trig_match = re.search(
            r'CREATE\s+TRIGGER\s+"?([a-zA-Z0-9_]+)"?\s+(.*?)\s+ON\s+(?:"?([a-zA-Z0-9_]+)"?\.)?"?([a-zA-Z0-9_]+)"?\s+(.*)',
            stmt,
            re.IGNORECASE | re.DOTALL,
        )
        if trig_match:
            trig_name = trig_match.group(1)
            schema = trig_match.group(3) or "public"
            table = trig_match.group(4)
            full_name = f"{schema}.{table}"
            if full_name in tables:
                tables[full_name]["triggers"][trig_name] = stmt.strip()

    if "public.alembic_version" in tables:
        del tables["public.alembic_version"]

    return tables, functions


def generate_html_report(
    json_data,
    sql_data,
    output_file="schema_diff_report.html",
    group_by="environment",
):
    json_tables, json_funcs = json_data
    sql_tables, sql_funcs = sql_data

    # Calculate Stats
    def get_stats(t_dict, f_dict):
        return {
            "Tables": len(t_dict),
            "Columns": sum(len(t["columns"]) for t in t_dict.values()),
            "Primary Key Columns": sum(len(t["pks"]) for t in t_dict.values()),
            "Unique Constraints": sum(len(t["uniques"]) for t in t_dict.values()),
            "Foreign Keys": sum(len(t["fks"]) for t in t_dict.values()),
            "Indexes": sum(len(t["indexes"]) for t in t_dict.values()),
            "Triggers": sum(len(t["triggers"]) for t in t_dict.values()),
            "Global Functions": len(f_dict),
        }

    json_stats = get_stats(json_tables, json_funcs)
    sql_stats = get_stats(sql_tables, sql_funcs)

    # Table Setup
    json_table_set = set(json_tables.keys())
    sql_table_set = set(sql_tables.keys())

    missing_in_sql = sorted(list(json_table_set - sql_table_set))
    missing_in_json = sorted(list(sql_table_set - json_table_set))
    common_tables = sorted(list(json_table_set.intersection(sql_table_set)))

    # Function Setup
    json_func_set = set(json_funcs.keys())
    sql_func_set = set(sql_funcs.keys())

    miss_func_sql = sorted(list(json_func_set - sql_func_set))
    miss_func_json = sorted(list(sql_func_set - json_func_set))

    common_funcs = sorted(list(json_func_set.intersection(sql_func_set)))
    diff_funcs = [f for f in common_funcs if json_funcs[f] != sql_funcs[f]]

    html = [
        f"<html><head><title>Database Schema Diff Report (Grouped by {group_by.capitalize()})</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; margin: 40px; background-color: #f9f9f9; color: #333; }",
        "h1, h2, h3 { color: #2c3e50; }",
        ".card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }",
        ".card-sql { border-left: 5px solid #c0392b; }",
        ".card-json { border-left: 5px solid #2980b9; }",
        ".missing { color: #c0392b; font-weight: bold; }",
        ".success { color: #27ae60; font-weight: bold; }",
        "ul, ol { line-height: 1.6; }",
        "code { background: #eee; padding: 2px 6px; border-radius: 4px; font-family: monospace; display: block; margin-top: 5px; white-space: pre-wrap;}",
        ".stats-table { width: 100%; border-collapse: collapse; margin-top: 10px; }",
        ".stats-table th, .stats-table td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }",
        ".stats-table th { background-color: #f0f4f8; color: #2c3e50; font-weight: bold; }",
        "</style></head><body>",
        f"<h1>Schema Comparison Report (Grouped by {group_by.capitalize()})</h1>",
    ]

    # --- ADD STATS SUMMARY PANEL ---
    html.append("<div class='card'><h2>📊 Analysis Summary</h2>")
    html.append("<table class='stats-table'>")
    html.append(
        "<tr><th>Object Type</th><th>JSON Blueprint</th><th>Physical SQL</th><th>Status</th></tr>"
    )

    for key in json_stats.keys():
        j_val = json_stats[key]
        s_val = sql_stats[key]
        status = (
            "<span class='success'>✅ Matches</span>"
            if j_val == s_val
            else "<span class='missing'>❌ Mismatch</span>"
        )
        html.append(
            f"<tr><td><b>{key}</b></td><td>{j_val:,}</td><td>{s_val:,}</td><td>{status}</td></tr>"
        )

    html.append("</table></div>")

    def format_tuple_list(t_list):
        return ", ".join([f"({', '.join(t)})" for t in t_list])

    def format_fk_list(fk_list):
        return ", ".join([f"({fk[0]} -> {fk[1]}.{fk[2]})" for fk in fk_list])

    if group_by == "environment":
        # SECTION 1: MISSING IN SQL
        html.append(
            "<div class='card card-sql'><h2>1. Missing in SQL (Requires DB Migration)</h2>"
        )
        sql_issues_found = False

        if missing_in_sql:
            sql_issues_found = True
            html.append("<h3>Entire Tables Missing:</h3><ul>")
            for t in missing_in_sql:
                html.append(f"<li class='missing'>{t}</li>")
            html.append("</ul>")

        # Global Functions Check
        if miss_func_sql or diff_funcs:
            sql_issues_found = True
            html.append("<h3>Global Functions Discrepancies:</h3><ul>")
            for f in miss_func_sql:
                html.append(
                    f"<li><span class='missing'>Missing Function:</span> <b>{f}</b></li>"
                )
            for f in diff_funcs:
                html.append(
                    f"<li><span class='missing'>Modified Function:</span> <b>{f}</b> (Definition mismatch)</li>"
                )
            html.append("</ul>")

        html.append("<h3>Object Discrepancies within Existing Tables:</h3><ol>")
        for table in common_tables:
            j_data = json_tables[table]
            s_data = sql_tables[table]

            miss_col_sql = j_data["columns"] - s_data["columns"]
            miss_pk_sql = j_data["pks"] - s_data["pks"]
            miss_uq_sql = j_data["uniques"] - s_data["uniques"]
            miss_fk_sql = j_data["fks"] - s_data["fks"]
            miss_idx_sql = set(j_data["indexes"].keys()) - set(s_data["indexes"].keys())
            miss_trig_sql = set(j_data["triggers"].keys()) - set(
                s_data["triggers"].keys()
            )

            if any(
                [
                    miss_col_sql,
                    miss_pk_sql,
                    miss_uq_sql,
                    miss_idx_sql,
                    miss_fk_sql,
                    miss_trig_sql,
                ]
            ):
                sql_issues_found = True
                html.append(f"<li><b>{table}</b><ul>")
                if miss_col_sql:
                    html.append(
                        f"<li><b>Columns:</b> <span class='missing'>{', '.join(miss_col_sql)}</span></li>"
                    )
                if miss_pk_sql:
                    html.append(
                        f"<li><b>Primary Keys:</b> <span class='missing'>{', '.join(miss_pk_sql)}</span></li>"
                    )
                if miss_uq_sql:
                    html.append(
                        f"<li><b>Unique Constraints:</b> <span class='missing'>{format_tuple_list(miss_uq_sql)}</span></li>"
                    )
                if miss_fk_sql:
                    html.append(
                        f"<li><b>Foreign Keys:</b> <span class='missing'>{format_fk_list(miss_fk_sql)}</span></li>"
                    )
                if miss_idx_sql:
                    html.append("<li><b>Indexes:</b><ul>")
                    for idx_key in miss_idx_sql:
                        obj = j_data["indexes"][idx_key]
                        name = obj["name"]
                        def_str = html_lib.escape(obj["raw"])
                        html.append(
                            f"<li><span class='missing'>{name}</span>: <code>{def_str}</code></li>"
                        )
                    html.append("</ul></li>")
                if miss_trig_sql:
                    html.append("<li><b>Triggers:</b><ul>")
                    for trig_key in miss_trig_sql:
                        def_str = html_lib.escape(j_data["triggers"][trig_key])
                        html.append(
                            f"<li><span class='missing'>{trig_key}</span>: <code>{def_str}</code></li>"
                        )
                    html.append("</ul></li>")
                html.append("</ul></li>")
        html.append("</ol>")
        if not sql_issues_found:
            html.append(
                "<p class='success'>✓ Physical Database is fully up to date.</p>"
            )
        html.append("</div>")

        # SECTION 2: MISSING IN JSON
        html.append(
            "<div class='card card-json'><h2>2. Missing in JSON (Requires Schema File Update)</h2>"
        )
        json_issues_found = False

        if missing_in_json:
            json_issues_found = True
            html.append("<h3>Entire Tables Missing:</h3><ul>")
            for t in missing_in_json:
                html.append(f"<li class='missing'>{t}</li>")
            html.append("</ul>")

        # Global Functions Check
        if miss_func_json or diff_funcs:
            json_issues_found = True
            html.append("<h3>Global Functions Discrepancies:</h3><ul>")
            for f in miss_func_json:
                html.append(
                    f"<li><span class='missing'>Missing Function:</span> <b>{f}</b></li>"
                )
            for f in diff_funcs:
                html.append(
                    f"<li><span class='missing'>Modified Function:</span> <b>{f}</b> (Definition mismatch)</li>"
                )
            html.append("</ul>")

        html.append("<h3>Object Discrepancies within Existing Tables:</h3><ol>")
        for table in common_tables:
            j_data = json_tables[table]
            s_data = sql_tables[table]

            miss_col_json = s_data["columns"] - j_data["columns"]
            miss_pk_json = s_data["pks"] - j_data["pks"]
            miss_uq_json = s_data["uniques"] - j_data["uniques"]
            miss_fk_json = s_data["fks"] - j_data["fks"]
            miss_idx_json = set(s_data["indexes"].keys()) - set(
                j_data["indexes"].keys()
            )
            miss_trig_json = set(s_data["triggers"].keys()) - set(
                j_data["triggers"].keys()
            )

            if any(
                [
                    miss_col_json,
                    miss_pk_json,
                    miss_uq_json,
                    miss_idx_json,
                    miss_fk_json,
                    miss_trig_json,
                ]
            ):
                json_issues_found = True
                html.append(f"<li><b>{table}</b><ul>")
                if miss_col_json:
                    html.append(
                        f"<li><b>Columns:</b> <span class='missing'>{', '.join(miss_col_json)}</span></li>"
                    )
                if miss_pk_json:
                    html.append(
                        f"<li><b>Primary Keys:</b> <span class='missing'>{', '.join(miss_pk_json)}</span></li>"
                    )
                if miss_uq_json:
                    html.append(
                        f"<li><b>Unique Constraints:</b> <span class='missing'>{format_tuple_list(miss_uq_json)}</span></li>"
                    )
                if miss_fk_json:
                    html.append(
                        f"<li><b>Foreign Keys:</b> <span class='missing'>{format_fk_list(miss_fk_json)}</span></li>"
                    )
                if miss_idx_json:
                    html.append("<li><b>Indexes:</b><ul>")
                    for idx_key in miss_idx_json:
                        obj = s_data["indexes"][idx_key]
                        name = obj["name"]
                        def_str = html_lib.escape(obj["raw"])
                        html.append(
                            f"<li><span class='missing'>{name}</span>: <code>{def_str}</code></li>"
                        )
                    html.append("</ul></li>")
                if miss_trig_json:
                    html.append("<li><b>Triggers:</b><ul>")
                    for trig_key in miss_trig_json:
                        def_str = html_lib.escape(s_data["triggers"][trig_key])
                        html.append(
                            f"<li><span class='missing'>{trig_key}</span>: <code>{def_str}</code></li>"
                        )
                    html.append("</ul></li>")
                html.append("</ul></li>")
        html.append("</ol>")
        if not json_issues_found:
            html.append(
                "<p class='success'>✓ Master JSON Schema is fully up to date.</p>"
            )
        html.append("</div>")

    else:
        # GROUP BY TABLE / GLOBAL
        html.append("<div class='card'><h2>Global Objects (Functions)</h2>")
        if not miss_func_sql and not miss_func_json and not diff_funcs:
            html.append(
                "<p class='success'>✓ All global functions match perfectly.</p>"
            )
        else:
            html.append("<ul>")
            for f in miss_func_sql:
                html.append(
                    f"<li><b>{f}</b>: <span class='missing'>Missing in SQL</span></li>"
                )
            for f in miss_func_json:
                html.append(
                    f"<li><b>{f}</b>: <span class='missing'>Missing in JSON</span></li>"
                )
            for f in diff_funcs:
                html.append(
                    f"<li><b>{f}</b>: <span class='missing'>Definition mismatch between JSON and SQL</span></li>"
                )
            html.append("</ul>")
        html.append("</div>")

        html.append("<div class='card'><h2>1. Entire Table Discrepancies</h2>")
        if not missing_in_sql and not missing_in_json:
            html.append("<p class='success'>✓ All tables match perfectly.</p>")
        else:
            if missing_in_sql:
                html.append(
                    f"<h3>Tables in JSON, MISSING in SQL:</h3><ul>{''.join([f'<li class="missing">{t}</li>' for t in missing_in_sql])}</ul>"
                )
            if missing_in_json:
                html.append(
                    f"<h3>Tables in SQL, MISSING in JSON:</h3><ul>{''.join([f'<li class="missing">{t}</li>' for t in missing_in_json])}</ul>"
                )
        html.append("</div>")

        html.append(
            "<div class='card'><h2>2. Object Discrepancies (Grouped by Table)</h2>"
        )
        discrepancies_found = False

        for table in common_tables:
            j_data = json_tables[table]
            s_data = sql_tables[table]

            miss_col_sql = j_data["columns"] - s_data["columns"]
            miss_col_json = s_data["columns"] - j_data["columns"]
            miss_pk_sql = j_data["pks"] - s_data["pks"]
            miss_pk_json = s_data["pks"] - j_data["pks"]
            miss_uq_sql = j_data["uniques"] - s_data["uniques"]
            miss_uq_json = s_data["uniques"] - j_data["uniques"]
            miss_fk_sql = j_data["fks"] - s_data["fks"]
            miss_fk_json = s_data["fks"] - j_data["fks"]

            j_idx_keys = set(j_data["indexes"].keys())
            s_idx_keys = set(s_data["indexes"].keys())
            miss_idx_sql = j_idx_keys - s_idx_keys
            miss_idx_json = s_idx_keys - j_idx_keys

            j_trig_keys = set(j_data["triggers"].keys())
            s_trig_keys = set(s_data["triggers"].keys())
            miss_trig_sql = j_trig_keys - s_trig_keys
            miss_trig_json = s_trig_keys - j_trig_keys

            if any(
                [
                    miss_col_sql,
                    miss_col_json,
                    miss_pk_sql,
                    miss_pk_json,
                    miss_uq_sql,
                    miss_uq_json,
                    miss_idx_sql,
                    miss_idx_json,
                    miss_fk_sql,
                    miss_fk_json,
                    miss_trig_sql,
                    miss_trig_json,
                ]
            ):
                discrepancies_found = True
                html.append(f"<h3>Table: {table}</h3><ul>")

                if miss_col_sql:
                    html.append(
                        f"<li><b>Columns</b> missing in SQL: <span class='missing'>{', '.join(miss_col_sql)}</span></li>"
                    )
                if miss_col_json:
                    html.append(
                        f"<li><b>Columns</b> missing in JSON: <span class='missing'>{', '.join(miss_col_json)}</span></li>"
                    )
                if miss_pk_sql:
                    html.append(
                        f"<li><b>Primary Keys</b> missing in SQL: <span class='missing'>{', '.join(miss_pk_sql)}</span></li>"
                    )
                if miss_pk_json:
                    html.append(
                        f"<li><b>Primary Keys</b> missing in JSON: <span class='missing'>{', '.join(miss_pk_json)}</span></li>"
                    )
                if miss_uq_sql:
                    html.append(
                        f"<li><b>Unique Constraints</b> missing in SQL: <span class='missing'>{format_tuple_list(miss_uq_sql)}</span></li>"
                    )
                if miss_uq_json:
                    html.append(
                        f"<li><b>Unique Constraints</b> missing in JSON: <span class='missing'>{format_tuple_list(miss_uq_json)}</span></li>"
                    )
                if miss_fk_sql:
                    html.append(
                        f"<li><b>Foreign Keys</b> missing in SQL: <span class='missing'>{format_fk_list(miss_fk_sql)}</span></li>"
                    )
                if miss_fk_json:
                    html.append(
                        f"<li><b>Foreign Keys</b> missing in JSON: <span class='missing'>{format_fk_list(miss_fk_json)}</span></li>"
                    )

                if miss_idx_sql:
                    html.append("<li><b>Indexes</b> missing in SQL:<ul>")
                    for idx_key in miss_idx_sql:
                        obj = j_data["indexes"][idx_key]
                        name = obj["name"]
                        def_str = html_lib.escape(obj["raw"])
                        html.append(
                            f"<li><span class='missing'>{name}</span>: <code>{def_str}</code></li>"
                        )
                    html.append("</ul></li>")

                if miss_idx_json:
                    html.append("<li><b>Indexes</b> missing in JSON:<ul>")
                    for idx_key in miss_idx_json:
                        obj = s_data["indexes"][idx_key]
                        name = obj["name"]
                        def_str = html_lib.escape(obj["raw"])
                        html.append(
                            f"<li><span class='missing'>{name}</span>: <code>{def_str}</code></li>"
                        )
                    html.append("</ul></li>")

                if miss_trig_sql:
                    html.append("<li><b>Triggers</b> missing in SQL:<ul>")
                    for trig_key in miss_trig_sql:
                        def_str = html_lib.escape(j_data["triggers"][trig_key])
                        html.append(
                            f"<li><span class='missing'>{trig_key}</span>: <code>{def_str}</code></li>"
                        )
                    html.append("</ul></li>")

                if miss_trig_json:
                    html.append("<li><b>Triggers</b> missing in JSON:<ul>")
                    for trig_key in miss_trig_json:
                        def_str = html_lib.escape(s_data["triggers"][trig_key])
                        html.append(
                            f"<li><span class='missing'>{trig_key}</span>: <code>{def_str}</code></li>"
                        )
                    html.append("</ul></li>")

                html.append("</ul>")

        if not discrepancies_found:
            html.append(
                "<p class='success'>✓ All database objects match perfectly.</p>"
            )

        html.append("</div>")

    html.append("</body></html>")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"\n✅ Analysis complete! Open '{output_file}' in your web browser.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pilot for Trades Schema Diff Tool")
    parser.add_argument(
        "--group-by",
        choices=["environment", "table"],
        default="environment",
        help="Choose how the report is formatted: by 'environment' (SQL vs JSON) or by 'table'.",
    )
    args = parser.parse_args()

    json_filename = "pilot-db-schema-v2.6h.json"
    sql_filename = "pilot-db-schema-dump-master.sql"
    output_filename = "schema_diff_report.html"

    print("Parsing JSON...")
    json_data = parse_json_schema(json_filename)

    print("Parsing SQL...")
    sql_data = parse_sql_schema(sql_filename)

    print(f"Generating Diff Report (Grouping by {args.group_by})...")
    generate_html_report(json_data, sql_data, output_filename, group_by=args.group_by)
