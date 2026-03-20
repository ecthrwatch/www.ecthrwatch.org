#!/usr/bin/env python3
"""
Publish Script - Combined Workflow
==================================

All-in-one script to publish a new version of the crime report.

Workflow:
1. Commit your working copy changes (to get a commit hash)
2. Archive the current published version
3. Update working copy with new version hash
4. Renumber paragraphs
5. Copy to index.en.md
6. Amend commit to include updated files

Usage:
    python3 publish.py --message "Added section on 2017 fraud"
    python3 publish.py --message "Fixed typos" --no-archive  # Skip archiving
    python3 publish.py --dry-run  # Preview without changes
"""

import re
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime


# Paths
SCRIPT_DIR = Path(__file__).parent
CRIME_REPORT_DIR = SCRIPT_DIR.parent.parent  # continuously_updated_crime_report_mcdonalds_rico_case/
WORKING_COPY = CRIME_REPORT_DIR / "working_copy_index.en.md"
INDEX_FILE = CRIME_REPORT_DIR / "index.en.md"


def run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command."""
    result = subprocess.run(['git'] + args, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Git error: {result.stderr}", file=sys.stderr)
        if check:
            sys.exit(1)
    return result


def get_commit_hash(short: bool = True) -> str:
    """Get the current HEAD commit hash."""
    args = ['rev-parse']
    if short:
        args.append('--short')
    args.append('HEAD')
    result = run_git(args)
    return result.stdout.strip()


def has_uncommitted_changes() -> bool:
    """Check if there are uncommitted changes."""
    result = run_git(['status', '--porcelain'], check=False)
    return bool(result.stdout.strip())


def commit_changes(message: str, files: list[Path] = None):
    """Commit specified files or all changes."""
    if files:
        for f in files:
            run_git(['add', str(f)])
    else:
        run_git(['add', '-A'])
    run_git(['commit', '-m', message])


def amend_commit():
    """Amend the current commit with staged changes."""
    run_git(['commit', '--amend', '--no-edit'])


def update_version_in_file(filepath: Path, commit_hash: str) -> tuple[str, int]:
    """Update version hash and renumber paragraphs in a file."""
    content = filepath.read_text(encoding='utf-8')

    # Pattern matches both formats
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

    # Update frontmatter
    today = datetime.now().strftime('%Y-%m-%d')

    # Remove old version fields
    updated = re.sub(r'\nversion_hash:.*', '', updated)
    updated = re.sub(r'\nversion_date:.*', '', updated)
    updated = re.sub(r'\nparagraph_count:.*', '', updated)

    # Add new version fields before closing ---
    if updated.startswith('---'):
        # Find end of frontmatter
        end_match = re.search(r'\n---\n', updated[3:])
        if end_match:
            insert_pos = end_match.start() + 3
            version_info = f'\nversion_hash: "{commit_hash}"\nversion_date: "{today}"\nparagraph_count: {counter}'
            updated = updated[:insert_pos] + version_info + updated[insert_pos:]

    filepath.write_text(updated, encoding='utf-8')
    return commit_hash, counter


def archive_current_version(latest_hash: str) -> bool:
    """Archive the current published version using archive_version.py."""
    if not INDEX_FILE.exists():
        print("No existing index.en.md to archive")
        return False

    archive_script = SCRIPT_DIR / "archive_version.py"
    if not archive_script.exists():
        print(f"Archive script not found: {archive_script}")
        return False

    result = subprocess.run(
        [sys.executable, str(archive_script), '--source', str(INDEX_FILE), '--latest-hash', latest_hash],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Archive failed: {result.stderr}")
        return False

    print(result.stdout)
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Publish a new version of the crime report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 publish.py --message "Added section on 2017 fraud"
    python3 publish.py --message "Minor fixes" --no-archive
    python3 publish.py --dry-run
        """
    )
    parser.add_argument(
        '--message', '-m',
        required=True,
        help='Commit message for the new version'
    )
    parser.add_argument(
        '--no-archive',
        action='store_true',
        help='Skip archiving the current version'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Preview what would be done without making changes'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("CRIME REPORT PUBLISH WORKFLOW")
    print("=" * 60)

    # Check working copy exists
    if not WORKING_COPY.exists():
        print(f"Error: Working copy not found: {WORKING_COPY}")
        sys.exit(1)

    print(f"\nWorking copy: {WORKING_COPY}")
    print(f"Target: {INDEX_FILE}")

    if args.dry_run:
        print("\n[DRY RUN MODE - No changes will be made]")

    # Step 1: Check for uncommitted changes and commit
    print("\n--- Step 1: Commit changes ---")
    if has_uncommitted_changes():
        print("Uncommitted changes detected")
        if not args.dry_run:
            commit_changes(args.message, [WORKING_COPY])
            print(f"Committed: {args.message}")
    else:
        print("No uncommitted changes, using current HEAD")

    # Get commit hash
    commit_hash = get_commit_hash(short=True)
    print(f"Commit hash: {commit_hash}")

    # Step 2: Archive current version (optional)
    if not args.no_archive:
        print("\n--- Step 2: Archive current version ---")
        if args.dry_run:
            if INDEX_FILE.exists():
                print(f"Would archive current index.en.md")
            else:
                print("No existing version to archive")
        else:
            archive_current_version(commit_hash)
    else:
        print("\n--- Step 2: Skipping archive (--no-archive) ---")

    # Step 3: Update version in working copy
    print("\n--- Step 3: Update version hash ---")
    if args.dry_run:
        content = WORKING_COPY.read_text(encoding='utf-8')
        pattern = re.compile(r'^\((?:version#[a-f0-9]+|DRAFT#\d+)\)\(\d+\)&emsp;', re.MULTILINE)
        count = len(pattern.findall(content))
        print(f"Would update {count} paragraphs to (version#{commit_hash})(N)")
    else:
        _, count = update_version_in_file(WORKING_COPY, commit_hash)
        print(f"Updated {count} paragraphs to (version#{commit_hash})(N)")

    # Step 4: Copy to index.en.md
    print("\n--- Step 4: Copy to index.en.md ---")
    if args.dry_run:
        print(f"Would copy {WORKING_COPY} -> {INDEX_FILE}")
    else:
        shutil.copy(WORKING_COPY, INDEX_FILE)
        print(f"Copied to {INDEX_FILE}")

    # Step 5: Amend commit with updated files
    print("\n--- Step 5: Amend commit ---")
    if args.dry_run:
        print("Would amend commit with updated files")
    else:
        run_git(['add', str(WORKING_COPY), str(INDEX_FILE)])
        # Also add archive files if they were created
        archive_dir = CRIME_REPORT_DIR.parent.parent / "archive" / "crime-report"
        if archive_dir.exists():
            run_git(['add', str(archive_dir)])
        amend_commit()
        print("Amended commit with all changes")

    # Summary
    print("\n" + "=" * 60)
    if args.dry_run:
        print("[DRY RUN COMPLETE - No changes made]")
    else:
        print("PUBLISH COMPLETE!")
        print(f"  Version: {commit_hash}")
        print(f"  Paragraphs: {count}")
        print(f"  Commit: {get_commit_hash(short=False)[:12]}...")
    print("=" * 60)


if __name__ == '__main__':
    main()
