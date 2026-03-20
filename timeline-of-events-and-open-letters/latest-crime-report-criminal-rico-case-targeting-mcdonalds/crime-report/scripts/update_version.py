#!/usr/bin/env python3
"""
Update Version Script
=====================

Updates the version hash in paragraph numbers to the current git commit hash.

Format: (version#HASH)(N)&emsp;

Usage:
    python3 update_version.py input.md [--output output.md] [--dry-run]

The script:
1. Gets the current git commit hash (short 7-char)
2. Updates all paragraph numbers: (version#OLD)(N) → (version#NEW)(N)
   Also handles legacy format: (DRAFT#NN)(N) → (version#HASH)(N)
3. Renumbers paragraphs sequentially (1 to N)
"""

import re
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


def get_git_commit_hash(short: bool = True) -> str | None:
    """Get the current git commit hash. Returns None if not in a git repo."""
    try:
        cmd = ['git', 'rev-parse', '--short' if short else '', 'HEAD']
        cmd = [c for c in cmd if c]  # Remove empty strings
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        return None


def update_version_and_renumber(content: str, commit_hash: str) -> tuple[str, int]:
    """
    Update version hash and renumber paragraphs.

    Handles both:
    - New format: (version#OLDHASH)(N)&emsp;
    - Legacy format: (DRAFT#NN)(N)&emsp;

    Returns:
        Tuple of (updated content, paragraph count)
    """
    # Pattern matches both formats at START of line
    # Group 1: The version/draft prefix (we'll replace it)
    # Group 2: The paragraph number (we'll replace it)
    # Group 3: The &emsp; separator (we'll keep it)
    pattern = re.compile(
        r'^(\((?:version#[a-f0-9]+|DRAFT#\d+)\))\((\d+)\)(&emsp;)',
        re.MULTILINE
    )

    counter = 0

    def replace_paragraph(match):
        nonlocal counter
        counter += 1
        return f'(version#{commit_hash})({counter})&emsp;'

    updated = pattern.sub(replace_paragraph, content)

    return updated, counter


def update_frontmatter_version(content: str, commit_hash: str, paragraph_count: int) -> str:
    """
    Update or add version info in frontmatter.

    Adds/updates:
    - version_hash
    - version_date
    - paragraph_count
    """
    # Check if content has frontmatter
    if not content.startswith('---'):
        return content

    # Find end of frontmatter
    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return content

    frontmatter_end = end_match.end() + 3
    frontmatter = content[:frontmatter_end]
    rest = content[frontmatter_end:]

    # Update or add version fields
    today = datetime.now().strftime('%Y-%m-%d')

    # Remove old version fields if they exist
    frontmatter = re.sub(r'\nversion_hash:.*', '', frontmatter)
    frontmatter = re.sub(r'\nversion_date:.*', '', frontmatter)
    frontmatter = re.sub(r'\nparagraph_count:.*', '', frontmatter)

    # Add new version fields before closing ---
    version_info = f"\nversion_hash: \"{commit_hash}\"\nversion_date: \"{today}\"\nparagraph_count: {paragraph_count}"
    frontmatter = frontmatter.rstrip('\n-')
    frontmatter = frontmatter.rstrip()
    if not frontmatter.endswith('\n'):
        frontmatter += '\n'
    frontmatter += f"{version_info}\n---\n"

    return frontmatter + rest


def main():
    parser = argparse.ArgumentParser(
        description='Update version hash in paragraph numbers'
    )
    parser.add_argument(
        'input_file',
        help='Input markdown file'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file (default: overwrite input)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be done without writing'
    )
    parser.add_argument(
        '--hash',
        help='Specify commit hash (default: current HEAD)'
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Get commit hash
    commit_hash = args.hash or get_git_commit_hash(short=True)
    if not commit_hash:
        print("Error: Not in a git repository and no --hash provided", file=sys.stderr)
        print("Hint: Use --hash XXXX to specify a version hash manually", file=sys.stderr)
        sys.exit(1)
    print(f"Using commit hash: {commit_hash}")

    # Read input
    content = input_path.read_text(encoding='utf-8')

    # Count existing paragraphs
    old_pattern = re.compile(r'^\((?:version#[a-f0-9]+|DRAFT#\d+)\)\(\d+\)&emsp;', re.MULTILINE)
    old_count = len(old_pattern.findall(content))
    print(f"Found {old_count} paragraphs")

    # Update version and renumber
    updated, new_count = update_version_and_renumber(content, commit_hash)

    print(f"Updated {new_count} paragraphs to (version#{commit_hash})(N)")

    if old_count != new_count:
        print(f"WARNING: Paragraph count changed! Before: {old_count}, After: {new_count}")

    # Update frontmatter
    updated = update_frontmatter_version(updated, commit_hash, new_count)

    # Show sample
    print("\nFirst 3 paragraphs:")
    new_pattern = re.compile(r'^\(version#[a-f0-9]+\)\(\d+\)&emsp;.*$', re.MULTILINE)
    samples = new_pattern.findall(updated)[:3]
    for sample in samples:
        if len(sample) > 100:
            sample = sample[:100] + "..."
        print(f"  {sample}")

    if args.dry_run:
        print("\n[DRY RUN] No files modified")
    else:
        output_path = Path(args.output) if args.output else input_path
        output_path.write_text(updated, encoding='utf-8')
        print(f"\nWritten to: {output_path}")


if __name__ == '__main__':
    main()
