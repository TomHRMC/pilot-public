#!/usr/bin/env python3
"""
Fix audit FK field definitions in all model files.
Replace sa_column_kwargs syntax with sa_column Column/ForeignKey syntax.
"""

import re
from pathlib import Path


def fix_file(filepath):
    """Fix FK constraints in a single file."""
    with open(filepath) as f:
        content = f.read()

    # Pattern to match the incorrect syntax
    pattern = r'(created_by|updated_by): Optional\[uuid\.UUID\] = Field\(\s*default=None,\s*foreign_key="user\.id",\s*sa_column_kwargs=\{"ondelete": "RESTRICT"\}\s*\)'

    # Replacement for created_by
    replacement_created = r'created_by: Optional[uuid.UUID] = Field(\n        default=None,\n        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"))\n    )'

    # Replacement for updated_by
    replacement_updated = r'updated_by: Optional[uuid.UUID] = Field(\n        default=None,\n        sa_column=Column(PG_UUID, ForeignKey("user.id", ondelete="RESTRICT"))\n    )'

    # Replace all instances
    new_content = content
    new_content = re.sub(
        r'created_by: Optional\[uuid\.UUID\] = Field\(\s*default=None,\s*foreign_key="user\.id",\s*sa_column_kwargs=\{"ondelete": "RESTRICT"\}\s*\)',
        replacement_created,
        new_content,
    )
    new_content = re.sub(
        r'updated_by: Optional\[uuid\.UUID\] = Field\(\s*default=None,\s*foreign_key="user\.id",\s*sa_column_kwargs=\{"ondelete": "RESTRICT"\}\s*\)',
        replacement_updated,
        new_content,
    )

    # Write back
    with open(filepath, "w") as f:
        f.write(new_content)

    print(f"✅ Fixed {filepath}")


# Fix all model files
model_files = [
    "app/models/auth.py",
    "app/models/quoting.py",
    "app/models/system.py",
]

for f in model_files:
    fix_file(Path(f))

print("\n✅ All files fixed!")
