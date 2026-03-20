#!/usr/bin/env python3
"""
Renumber paragraphs sequentially in continuous thesis-style format.

Use this after inserting or deleting paragraphs to fix the numbering.

Format expected: (DRAFT#NN)(number)&emsp;

Usage:
  python3 renumber_paragraphs.py input.md [--draft 32] [--dry-run]
"""

import re
import sys
import argparse
from pathlib import Path


def renumber_paragraphs(content: str, draft_number: int = 32) -> tuple[str, int]:
    """
    Renumber all paragraphs sequentially.

    Returns:
        Tuple of (renumbered content, paragraph count)
    """
    # Pattern matches: (DRAFT#NN)(number)&emsp; at start of line
    pattern = re.compile(
        r'^(\(DRAFT#\d+\))\((\d+)\)(&emsp;)',
        re.MULTILINE
    )

    counter = 0

    def replace_paragraph(match):
        nonlocal counter
        counter += 1
        return f'(DRAFT#{draft_number})({counter})&emsp;'

    renumbered = pattern.sub(replace_paragraph, content)

    return renumbered, counter


def main():
    parser = argparse.ArgumentParser(
        description='Renumber paragraphs sequentially in continuous format'
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
        '--draft', '-d',
        type=int,
        default=32,
        help='Draft number to use (default: 32)'
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Read input
    content = input_path.read_text(encoding='utf-8')

    # Check current format
    old_format_pattern = re.compile(r'^\(DRAFT#\d+\)(\([^)]+\))+\(\d+\)&emsp;', re.MULTILINE)
    old_format_count = len(old_format_pattern.findall(content))
    if old_format_count > 0:
        print(f"WARNING: Found {old_format_count} paragraphs in OLD format (per-section).")
        print("Use convert_to_continuous_numbering.py first!")
        sys.exit(1)

    # Count paragraphs before
    new_format_pattern = re.compile(r'^\(DRAFT#\d+\)\(\d+\)&emsp;', re.MULTILINE)
    before_count = len(new_format_pattern.findall(content))
    print(f"Found {before_count} paragraphs")

    # Renumber
    renumbered, after_count = renumber_paragraphs(content, args.draft)

    print(f"Renumbered {after_count} paragraphs (DRAFT#{args.draft})")

    if before_count != after_count:
        print(f"WARNING: Paragraph count changed! Before: {before_count}, After: {after_count}")

    # Show first and last paragraphs
    new_matches = new_format_pattern.findall(renumbered)
    if new_matches:
        print(f"\nFirst paragraph: {new_matches[0]}...")
        print(f"Last paragraph: {new_matches[-1]}...")

    if args.dry_run:
        print("\n[DRY RUN] No files modified")
    else:
        output_path = Path(args.output) if args.output else input_path
        output_path.write_text(renumbered, encoding='utf-8')
        print(f"\nWritten to: {output_path}")


if __name__ == '__main__':
    main()
