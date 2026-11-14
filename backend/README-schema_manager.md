# Pilot Schema Management Instructions & Constraints

You are responsible for safely interacting with the Pilot project's master database schema JSON file (e.g., `pilot-db-schema-v2.6h.json`). 

The schema is managed by `schema_manager.py`, a universal, path-based JSON mutator. It uses **dot-notation** to traverse the schema tree, allowing you to read, create, update, or delete any object, anywhere in the file.

### 🛑 CRITICAL CONSTRAINTS
1. **NEVER use `sed`, `awk`, `grep`, or inline Python scripts to mutate the schema JSON file directly.** Line-based editing will corrupt the JSON syntax and break the application.
2. **ALWAYS use the `schema_manager.py` tool** located at `backend/schema_manager.py` for all schema interactions.
3. **Use Temporary Payload Files for Complex JSON:** While the script supports `--value` for simple strings or numbers, **always** write dictionaries or arrays to a temporary file (`temp_payload.json`), pass the file to the script using `--payload`, and then clean it up. This prevents CLI quote-escaping nightmares.

---

## 🧭 The Path-Based System

The script navigates the JSON schema using dot-separated paths.
* **Root Level:** `version`, `functions`, `design_decisions`, `tables`
* **Table Level:** `tables.user`, `tables.invoice`
* **Column Level:** `tables.user.columns.email`
* **Table Arrays:** `tables.user.indexes`, `tables.user.foreign_keys`, `tables.user.triggers`

---

## 🛠 Command Reference & Examples

### 1. `get` (View Data)
Reads and prints the JSON object at the specified path.

* **View a full table definition:**
    ```bash
    python schema_manager.py get --path tables.user
    ```
* **View a specific column:**
    ```bash
    python schema_manager.py get --path tables.user.columns.email
    ```
* **View all global functions:**
    ```bash
    python schema_manager.py get --path functions
    ```

### 2. `set` (Add or Overwrite Objects/Attributes)
Creates a new key or completely overwrites an existing one. Use this for Columns, Tables, and flat Attributes (like comments or primary keys).

* **Update a top-level string (Version):**
    ```bash
    python schema_manager.py set --path version --value '"v2.7a"'
    ```
* **Update a Table Comment:**
    ```bash
    python schema_manager.py set --path tables.invoice.comment --value '"The final legal billing record."'
    ```
* **Set a Primary Key (Array of strings):**
    ```bash
    python schema_manager.py set --path tables.tenant_user.primary_key --value '["tenant_id", "user_id"]'
    ```
* **Add or Overwrite a Column:**
    ```bash
    cat << 'EOF' > temp.json
    {
      "type": "timestamptz",
      "nullable": true,
      "description": "When the user was suspended."
    }
    EOF
    python schema_manager.py set --path tables.user.columns.suspended_at --payload temp.json
    ```

### 3. `delete` (Remove Objects/Attributes)
Permanently deletes a key from a dictionary.

* **Delete a specific column:**
    ```bash
    python schema_manager.py delete --path tables.user.columns.obsolete_column
    ```
* **Delete an entire table:**
    ```bash
    python schema_manager.py delete --path tables.deprecated_table
    ```

### 4. `array-append` (Add to Lists)
Appends a new object to an array. Use this for Indexes, Foreign Keys, Constraints, Triggers, Seed Rows, and Global Functions.

* **Add a Global Function:**
    ```bash
    python schema_manager.py array-append --path functions --payload new_func.json
    ```
* **Add a Foreign Key:**
    ```bash
    cat << 'EOF' > temp.json
    {
      "name": "fk_invoice_customer",
      "columns": ["customer_id"],
      "ref_table": "customer",
      "ref_columns": ["id"],
      "on_delete": "RESTRICT"
    }
    EOF
    python schema_manager.py array-append --path tables.invoice.foreign_keys --payload temp.json
    ```
* **Add an Index:**
    ```bash
    cat << 'EOF' > temp.json
    {
      "name": "idx_invoice_customer",
      "definition": "(customer_id)"
    }
    EOF
    python schema_manager.py array-append --path tables.invoice.indexes --payload temp.json
    ```
* **Add a Check Constraint:**
    ```bash
    cat << 'EOF' > temp.json
    {
      "name": "chk_job_estimated_duration_positive",
      "definition": "(estimated_duration_minutes IS NULL OR estimated_duration_minutes > 0)"
    }
    EOF
    python schema_manager.py array-append --path tables.job.check_constraints --payload temp.json
    ```
* **Add an Exclusion Constraint:**
    ```bash
    cat << 'EOF' > temp.json
    {
      "name": "piv_no_overlap",
      "using": "gist",
      "definition": "(tenant_id WITH =, pricebook_item_id WITH =, valid_period WITH &&)"
    }
    EOF
    python schema_manager.py array-append --path tables.pricebook_item_version.exclusion_constraints --payload temp.json
    ```
* **Add a Trigger:**
    ```bash
    cat << 'EOF' > temp.json
    {
      "name": "audit_user_changes",
      "definition": "CREATE TRIGGER audit_user_changes AFTER INSERT OR DELETE OR UPDATE ON public.\"user\" FOR EACH ROW EXECUTE FUNCTION audit.log_changes()"
    }
    EOF
    python schema_manager.py array-append --path tables.user.triggers --payload temp.json
    ```
* **Add a Unique Constraint:**
    ```bash
    python schema_manager.py array-append --path tables.user_sso_identity.unique --value '["sso_provider_code", "provider_user_id"]'
    ```
* **Add a Seed Row:**
    ```bash
    cat << 'EOF' > temp.json
    {
      "code": "usd",
      "name": "US Dollar",
      "symbol": "$"
    }
    EOF
    python schema_manager.py array-append --path tables.currency.seed_rows --payload temp.json
    ```
* **Add a Design Decision:**
    ```bash
    cat << 'EOF' > temp.json
    {
      "topic": "Soft Deletes",
      "decision": "Use boolean is_active instead of deleted_at.",
      "date": "2026-05-12"
    }
    EOF
    python schema_manager.py array-append --path design_decisions --payload temp.json
    ```

### 5. `array-remove` (Remove from Lists)
Removes an object from an array based on a specific key/value pair match.

* **Remove a Trigger by Name:**
    ```bash
    python schema_manager.py array-remove \
      --path tables.user.triggers \
      --match-key name \
      --match-value audit_user_changes
    ```
* **Remove a Global Function by Name:**
    ```bash
    python schema_manager.py array-remove \
      --path functions \
      --match-key name \
      --match-value log_changes
    ```

### 6. `array-update` (Update Lists In-Place)
Finds an object inside an array matching a key/value pair, and entirely replaces it with your new payload.

* **Update a Global Function In-Place:**
    ```bash
    python schema_manager.py array-update \
      --path functions \
      --match-key name \
      --match-value log_changes \
      --payload updated_log_changes.json
    ```
* **Update an existing Index In-Place:**
    ```bash
    cat << 'EOF' > temp.json
    {
      "name": "idx_invoice_customer",
      "definition": "(tenant_id, customer_id)"
    }
    EOF
    python schema_manager.py array-update \
      --path tables.invoice.indexes \
      --match-key name \
      --match-value idx_invoice_customer \
      --payload temp.json
    ```

---

## 🔄 Standard Workflow for Schema Updates

**Step 1: Check the Current State**
Verify the structure you are about to modify to understand the current schema configuration.
```bash
python schema_manager.py get --path tables.job.columns
```

**Step 2: Prepare the Payload**
Write the exact JSON structure for your update into a temporary file. Ensure strings and lists are strictly formatted as valid JSON.

```bash
cat << 'EOF' > temp_payload.json
{
  "type": "text",
  "nullable": true,
  "description": "Optional integration ID from external system."
}
EOF
```

**Step 3: Execute the Mutation**
Use the appropriate command (`set`, `array-append`, `array-update`) to safely apply your changes.

```bash
python schema_manager.py set --path tables.job.columns.external_id --payload temp_payload.json
```

**Step 4: Clean Up**
Always delete your temporary payload file after a successful operation to keep the workspace clean.

```bash
rm temp_payload.json
```