import json
import sys
from datetime import UTC, datetime

from app.main import app  # <-- Import your FastAPI app instance

# ---------------------------------------------------------------------------
# Schema map helpers
# ---------------------------------------------------------------------------


def _resolve_schema_ref(schema_obj, full_spec):
    """Follow a $ref if present, otherwise return the object itself."""
    if "$ref" in schema_obj:
        ref_path = schema_obj["$ref"].lstrip("#/").split("/")
        node = full_spec
        for part in ref_path:
            node = node.get(part, {})
            if not isinstance(node, dict):
                return {}
        return node
    return schema_obj


def _schema_to_example(schema_obj, full_spec, depth=0):
    """Generate a simple example JSON structure from a schema (max 2 levels deep)."""
    if depth > 2:
        return "..."
    resolved = _resolve_schema_ref(schema_obj, full_spec)
    obj_type = resolved.get("type")
    if obj_type == "object":
        props = resolved.get("properties", {})
        return {
            k: _schema_to_example(v, full_spec, depth + 1)
            for k, v in list(props.items())[:8]
        }
    elif obj_type == "array":
        items = resolved.get("items", {})
        return [_schema_to_example(items, full_spec, depth + 1)]
    elif obj_type == "string":
        return resolved.get("example", "string")
    elif obj_type == "integer":
        return resolved.get("example", 0)
    elif obj_type == "boolean":
        return False
    elif obj_type == "number":
        return 0.0
    else:
        return resolved.get("title", "object")


def _format_request_body(operation, full_spec):
    """Return a markdown block for the request body, or empty string if none."""
    rb = operation.get("requestBody")
    if not rb:
        return ""
    content = rb.get("content", {})
    json_content = content.get("application/json", {})
    schema_obj = json_content.get("schema", {})
    if not schema_obj:
        return ""

    resolved = _resolve_schema_ref(schema_obj, full_spec)
    title = resolved.get("title", schema_obj.get("$ref", "").split("/")[-1] or "Body")
    example = _schema_to_example(schema_obj, full_spec)

    lines = [f"**Request body**: `{title}`"]
    lines.append("```json")
    lines.append(json.dumps(example, indent=2))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _format_responses(operation, full_spec):
    """Return a markdown block for the responses."""
    responses = operation.get("responses", {})
    if not responses:
        return ""

    lines = []
    for status_code, resp_obj in sorted(responses.items()):
        desc = resp_obj.get("description", "")
        content = resp_obj.get("content", {})
        json_content = content.get("application/json", {})
        schema_obj = json_content.get("schema", {})

        if schema_obj:
            resolved = _resolve_schema_ref(schema_obj, full_spec)
            title = resolved.get(
                "title", schema_obj.get("$ref", "").split("/")[-1] or ""
            )
            if title:
                lines.append(f"**Response {status_code}**: `{title}`")
            else:
                lines.append(f"**Response {status_code}**: {desc}")
            example = _schema_to_example(schema_obj, full_spec)
            if isinstance(example, (dict, list)) and example:
                lines.append("```json")
                lines.append(json.dumps(example, indent=2))
                lines.append("```")
        else:
            lines.append(f"**Response {status_code}**: {desc}")
        lines.append("")

    return "\n".join(lines)


def export_schema_map(schema, map_path):
    """Generate a human/agent-readable Markdown summary of all API endpoints."""
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Group endpoints by first tag
    by_tag: dict[
        str, list[tuple[str, str, dict]]
    ] = {}  # tag -> [(path, method, operation)]

    paths = schema.get("paths", {})
    for path_str, path_item in sorted(paths.items()):
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            operation = path_item.get(method)
            if not operation:
                continue
            tags = operation.get("tags", ["untagged"])
            tag = tags[0] if tags else "untagged"
            by_tag.setdefault(tag, [])
            by_tag[tag].append((path_str, method.upper(), operation))

    lines = [
        "# Pilot for Trades — OpenAPI Schema Map",
        "",
        f"**Generated**: {generated_at}  ",
        "**Source**: openapi.json  ",
        "**Purpose**: Human/agent-readable endpoint summary. "
        "Check this before writing any frontend hook or backend route.",
        "",
        "---",
        "",
        "## Endpoints by Tag",
        "",
    ]

    for tag in sorted(by_tag.keys()):
        lines.append(f"### {tag}")
        lines.append("")

        for path_str, method, operation in by_tag[tag]:
            summary = operation.get("summary", "")
            description = operation.get("description", "")

            lines.append(f"#### `{method} {path_str}`")
            if summary:
                lines.append(f"**Summary**: {summary}  ")

            # Auth
            security = operation.get("security")
            if security is not None:
                if security:
                    lines.append("**Auth**: Required  ")
                else:
                    lines.append("**Auth**: None  ")
            lines.append("")

            # Query / path params
            parameters = operation.get("parameters", [])
            if parameters:
                lines.append("**Parameters**:")
                for param in parameters:
                    p_name = param.get("name", "")
                    p_in = param.get("in", "")
                    p_required = param.get("required", False)
                    p_schema = param.get("schema", {})
                    p_type = p_schema.get("type", "")
                    p_default = p_schema.get("default")
                    p_desc = param.get("description", "")

                    required_label = "required" if p_required else "optional"
                    default_label = (
                        f", default: {p_default}" if p_default is not None else ""
                    )
                    desc_label = f" — {p_desc}" if p_desc else ""
                    lines.append(
                        f"- `{p_name}` ({p_in}, {p_type}, {required_label}{default_label}){desc_label}"
                    )
                lines.append("")

            # Request body
            rb_block = _format_request_body(operation, schema)
            if rb_block:
                lines.append(rb_block)

            # Responses
            resp_block = _format_responses(operation, schema)
            if resp_block:
                lines.append(resp_block)

            lines.append("---")
            lines.append("")

    with open(map_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Main export
# ---------------------------------------------------------------------------


def export_schema(output_path="openapi.json", map_path="openapi_schema_map.md"):
    try:
        # FastAPI's built-in method to generate the OpenAPI schema dictionary
        schema = app.openapi()

        # Always write openapi.json
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"✅ Successfully exported OpenAPI schema to {output_path}")

        # Always write openapi_schema_map.md
        export_schema_map(schema, map_path)
        print(f"✅ Successfully exported OpenAPI schema map to {map_path}")

    except Exception as e:
        print(f"❌ Failed to export schema: {e}")
        sys.exit(1)


if __name__ == "__main__":
    export_schema()
