#!/usr/bin/env python3
"""
Migrate paragraph numbers from (version#initial)(N) format to just (N).
This is a one-time migration script.
"""

import re
import sys
from pathlib import Path


def migrate_paragraph_format(input_file: str) -> None:
    """Remove (version#...) prefix from paragraph numbers."""

    content = Path(input_file).read_text(encoding='utf-8')

    # Pattern: (version#anything)(number) -> (number)
    # Captures the number to preserve it
    pattern = r'\(version#[a-zA-Z0-9_-]+\)\((\d+)\)'

    # Count matches before migration
    matches = re.findall(pattern, content)
    print(f"Found {len(matches)} paragraph numbers to migrate")

    # Replace (version#...)(N) with just (N)
    new_content = re.sub(pattern, r'(\1)', content)

    # Verify the migration
    remaining = re.findall(r'\(version#[a-zA-Z0-9_-]+\)\(\d+\)', new_content)
    if remaining:
        print(f"WARNING: {len(remaining)} patterns still remain!")
        sys.exit(1)

    # Write the migrated content
    Path(input_file).write_text(new_content, encoding='utf-8')
    print(f"Migration complete. Converted {len(matches)} paragraph numbers.")
    print(f"Format changed from (version#initial)(N) to (N)")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 migrate_paragraph_format.py <input_file>")
        sys.exit(1)

    migrate_paragraph_format(sys.argv[1])
