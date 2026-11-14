import re


def main():
    sql_file = "schema_dump_latest.sql"  # <-- UPDATE THIS with your filename

    try:
        with open(sql_file, "r", encoding="utf-8") as f:
            content = f.read()

        print("--- SAMPLE CREATE TABLE STATEMENT ---")
        create_table_match = re.search(
            r"CREATE TABLE[\s\S]*?\);", content, re.IGNORECASE
        )
        if create_table_match:
            print(create_table_match.group(0))
        else:
            print("No CREATE TABLE statement found.")

        print("\n--- SAMPLE ALTER TABLE STATEMENT ---")
        alter_table_match = re.search(r"ALTER TABLE[\s\S]*?;", content, re.IGNORECASE)
        if alter_table_match:
            print(alter_table_match.group(0))
        else:
            print("No ALTER TABLE statement found.")

    except Exception as e:
        print(f"Error reading SQL: {e}")


if __name__ == "__main__":
    main()
