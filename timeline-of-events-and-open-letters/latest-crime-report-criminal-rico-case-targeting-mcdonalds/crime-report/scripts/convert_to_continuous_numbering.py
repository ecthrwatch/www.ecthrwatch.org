#!/usr/bin/env python3
"""
Convert paragraph numbering from complex per-section format to continuous thesis-style.

BEFORE:
  (DRAFT#29)(EXECUTIVE SUMMARY)(1)&emsp;Text...
  (DRAFT#29)(I)(A)(1)&emsp;Text...
  (DRAFT#29)(I)(C)(a)(1)&emsp;Text...
  (DRAFT#32)(IV)(CC)(1)&emsp;Text...

AFTER:
  (DRAFT#32)(1)&emsp;Text...
  (DRAFT#32)(2)&emsp;Text...
  (DRAFT#32)(3)&emsp;Text...
  etc.

Usage:
  python3 convert_to_continuous_numbering.py input.md [--output output.md] [--dry-run]
"""

import re
import sys
import argparse
from pathlib import Path


def convert_to_continuous_numbering(content: str, draft_number: int = 32) -> tuple[str, int]:
    """
    Convert all paragraph numbers to continuous format.

    Returns:
        Tuple of (converted content, paragraph count)
    """
    # Pattern matches paragraph numbers at START of line:
    # - (DRAFT#NN) followed by one or more (...) sections, ending with (number)
    # - Followed by either &emsp; or a space
    # Examples:
    #   (DRAFT#29)(EXECUTIVE SUMMARY)(1)&emsp;
    #   (DRAFT#29)(I)(A)(1)&emsp;
    #   (DRAFT#29)(I)(C)(a)(1)&emsp;
    #   (DRAFT#32)(IV)(EE)(74)&emsp;
    #   (DRAFT#29)(V)(K)(1) Text (space after closing paren)
    pattern = re.compile(
        r'^(\(DRAFT#\d+\))(\([^)]+\))+\((\d+)\)(&emsp;| )',
        re.MULTILINE
    )

    counter = 0

    def replace_paragraph(match):
        nonlocal counter
        counter += 1
        # Return new format: (DRAFT#NN)(counter)&emsp;
        # Always use &emsp; in the output for consistency
        return f'(DRAFT#{draft_number})({counter})&emsp;'

    converted = pattern.sub(replace_paragraph, content)

    return converted, counter


def main():
    parser = argparse.ArgumentParser(
        description='Convert paragraph numbering to continuous thesis-style format'
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

    # Count paragraphs before conversion
    old_pattern = re.compile(r'^\(DRAFT#\d+\)(\([^)]+\))+\(\d+\)&emsp;', re.MULTILINE)
    old_count = len(old_pattern.findall(content))
    print(f"Found {old_count} paragraphs in original file")

    # Convert
    converted, new_count = convert_to_continuous_numbering(content, args.draft)

    print(f"Converted {new_count} paragraphs to continuous numbering (DRAFT#{args.draft})")

    if old_count != new_count:
        print(f"WARNING: Paragraph count mismatch! Before: {old_count}, After: {new_count}")

    # Show sample conversions
    print("\nSample conversions (first 5):")
    new_pattern = re.compile(r'^\(DRAFT#\d+\)\(\d+\)&emsp;.*$', re.MULTILINE)
    samples = new_pattern.findall(converted)[:5]
    for sample in samples:
        # Truncate long lines
        if len(sample) > 100:
            sample = sample[:100] + "..."
        print(f"  {sample}")

    if args.dry_run:
        print("\n[DRY RUN] No files modified")
    else:
        output_path = Path(args.output) if args.output else input_path
        output_path.write_text(converted, encoding='utf-8')
        print(f"\nWritten to: {output_path}")


if __name__ == '__main__':
    main()
