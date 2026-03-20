#!/usr/bin/env python3
"""
Archive Version Script
======================

Archives the current published version before publishing a new one.

Creates a copy in /content/en/archive/crime-report/version-HASH/ with:
- Archive frontmatter (noindex, canonical URL, warning flag)
- Updates to the version history index page

Usage:
    python3 archive_version.py [--source path/to/index.en.md]
"""

import re
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime


# Paths relative to the ecthrwatch.org content directory
CONTENT_BASE = Path(__file__).parent.parent.parent.parent.parent  # content/en/
ARCHIVE_DIR = CONTENT_BASE / "archive" / "crime-report"
SOURCE_DIR = CONTENT_BASE / "timeline-of-events-and-open-letters" / "continuously_updated_crime_report_mcdonalds_rico_case"
LATEST_URL = "/timeline-of-events-and-open-letters/continuously_updated_crime_report_mcdonalds_rico_case/"


def extract_version_hash(content: str) -> str | None:
    """Extract the version hash from the first paragraph."""
    match = re.search(r'\(version#([a-f0-9]+)\)\(\d+\)&emsp;', content)
    if match:
        return match.group(1)

    # Try legacy format
    match = re.search(r'\(DRAFT#(\d+)\)\(\d+\)&emsp;', content)
    if match:
        return f"draft{match.group(1)}"

    return None


def extract_frontmatter_field(content: str, field: str) -> str | None:
    """Extract a field value from frontmatter."""
    match = re.search(rf'^{field}:\s*["\']?([^"\'\n]+)["\']?', content, re.MULTILINE)
    return match.group(1) if match else None


def count_paragraphs(content: str) -> int:
    """Count the number of paragraphs."""
    pattern = re.compile(r'^\((?:version#[a-f0-9]+|DRAFT#\d+)\)\(\d+\)&emsp;', re.MULTILINE)
    return len(pattern.findall(content))


def create_archive_frontmatter(
    original_content: str,
    version_hash: str,
    version_date: str,
    paragraph_count: int,
    latest_hash: str | None = None
) -> str:
    """Create archive frontmatter with noindex and canonical URL."""

    # Extract original title
    original_title = extract_frontmatter_field(original_content, 'title') or "Crime Report"

    frontmatter = f'''---
title: "{original_title} (Archived Version {version_hash})"
description: "Archived version of the crime report. Please see the latest version."
is_archived: true
version_hash: "{version_hash}"
version_date: "{version_date}"
latest_url: "{LATEST_URL}"
latest_hash: "{latest_hash or 'unknown'}"
paragraph_count: {paragraph_count}
robots: "noindex, nofollow"
canonical: "https://www.ecthrwatch.org{LATEST_URL}"
draft: false
---
'''
    return frontmatter


def update_content_for_archive(content: str) -> str:
    """
    Update content for archive:
    - Remove original frontmatter
    - Keep everything else
    """
    # Remove frontmatter
    if content.startswith('---'):
        end_match = re.search(r'\n---\n', content[3:])
        if end_match:
            content = content[end_match.end() + 3:]

    return content


def update_version_history_index(archive_dir: Path, version_hash: str, version_date: str, paragraph_count: int):
    """Update the _index.md version history page."""
    index_path = archive_dir / "_index.md"

    if index_path.exists():
        index_content = index_path.read_text(encoding='utf-8')
    else:
        # Create new index
        index_content = '''---
title: "Crime Report Version History"
description: "Archive of all previous versions of the crime report"
layout: "archive-list"
---

## Version History

All previous versions of the crime report are preserved below for reference and legal traceability.

**[→ Go to Latest Version](/timeline-of-events-and-open-letters/continuously_updated_crime_report_mcdonalds_rico_case/)**

| Version | Date | Paragraphs |
|---------|------|------------|
'''

    # Add new version entry to table
    new_entry = f"| [`{version_hash}`](version-{version_hash}/) | {version_date} | {paragraph_count} |\n"

    # Insert after table header (find the |---| line)
    lines = index_content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('|---'):
            lines.insert(i + 1, new_entry.strip())
            break

    index_content = '\n'.join(lines)
    index_path.write_text(index_content, encoding='utf-8')
    print(f"Updated version history: {index_path}")


def archive_version(source_path: Path, latest_hash: str | None = None) -> str | None:
    """
    Archive the current version.

    Returns the archived version hash, or None if nothing to archive.
    """
    if not source_path.exists():
        print(f"Source file not found: {source_path}")
        return None

    content = source_path.read_text(encoding='utf-8')

    # Extract version info
    version_hash = extract_version_hash(content)
    if not version_hash:
        print("Could not extract version hash from source file")
        return None

    version_date = extract_frontmatter_field(content, 'version_date')
    if not version_date:
        version_date = datetime.now().strftime('%Y-%m-%d')

    paragraph_count = count_paragraphs(content)

    # Check if already archived
    archive_path = ARCHIVE_DIR / f"version-{version_hash}"
    if archive_path.exists():
        print(f"Version {version_hash} already archived")
        return version_hash

    # Create archive directory
    archive_path.mkdir(parents=True, exist_ok=True)

    # Create archive content
    archive_frontmatter = create_archive_frontmatter(
        content, version_hash, version_date, paragraph_count, latest_hash
    )
    archive_body = update_content_for_archive(content)
    archive_content = archive_frontmatter + archive_body

    # Write archive file
    archive_file = archive_path / "index.md"
    archive_file.write_text(archive_content, encoding='utf-8')
    print(f"Archived version {version_hash} to: {archive_file}")

    # Copy images directory if it exists
    source_images = source_path.parent / "images"
    if source_images.exists():
        archive_images = archive_path / "images"
        if not archive_images.exists():
            shutil.copytree(source_images, archive_images)
            print(f"Copied images to archive")

    # Update version history index
    update_version_history_index(ARCHIVE_DIR, version_hash, version_date, paragraph_count)

    return version_hash


def main():
    parser = argparse.ArgumentParser(
        description='Archive the current published version'
    )
    parser.add_argument(
        '--source', '-s',
        default=None,
        help='Source file to archive (default: index.en.md in crime report directory)'
    )
    parser.add_argument(
        '--latest-hash',
        help='Hash of the new version being published (for reference in archive)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be done without writing'
    )

    args = parser.parse_args()

    if args.source:
        source_path = Path(args.source)
    else:
        source_path = SOURCE_DIR / "index.en.md"

    print(f"Content base: {CONTENT_BASE}")
    print(f"Archive dir: {ARCHIVE_DIR}")
    print(f"Source: {source_path}")

    if args.dry_run:
        content = source_path.read_text(encoding='utf-8')
        version_hash = extract_version_hash(content)
        paragraph_count = count_paragraphs(content)
        print(f"\n[DRY RUN] Would archive:")
        print(f"  Version: {version_hash}")
        print(f"  Paragraphs: {paragraph_count}")
        print(f"  To: {ARCHIVE_DIR / f'version-{version_hash}'}")
    else:
        archived_hash = archive_version(source_path, args.latest_hash)
        if archived_hash:
            print(f"\nSuccessfully archived version: {archived_hash}")
        else:
            print("\nNo version archived")
            sys.exit(1)


if __name__ == '__main__':
    main()
