#!/bin/bash
#
# Stamp the current git hash into index.en.md for publishing.
#
# Updates:
#   - version_hash in front matter
#   - version_date in front matter
#
# Usage:
#   ./stamp_version.sh
#

set -e

# Get script directory and navigate to content directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRIME_REPORT_DIR="$(dirname "$SCRIPT_DIR")"
CONTENT_DIR="$(dirname "$CRIME_REPORT_DIR")"
INDEX_FILE="$CONTENT_DIR/index.en.md"

cd "$CONTENT_DIR"

# Check if we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "Warning: You have uncommitted changes."
    echo "It's recommended to commit your changes first, then run this script."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get the current git hash (short, 7 characters)
GIT_HASH=$(git rev-parse --short HEAD)
VERSION_DATE=$(date "+%Y-%m-%d")

echo "=== Stamping Version ==="
echo "Git hash:     $GIT_HASH"
echo "Version date: $VERSION_DATE"
echo "Target file:  $INDEX_FILE"
echo ""

# Update version_hash in front matter
sed -i '' "s/^version_hash:.*$/version_hash: \"$GIT_HASH\"/" "$INDEX_FILE"

# Update version_date in front matter
sed -i '' "s/^version_date:.*$/version_date: \"$VERSION_DATE\"/" "$INDEX_FILE"

echo "Version stamped successfully!"
echo ""
echo "Front matter updated:"
grep -E "^version_hash:|^version_date:" "$INDEX_FILE"
echo ""
echo "Next steps:"
echo "  1. Review the changes: git diff index.en.md"
echo "  2. Commit: git add index.en.md && git commit -m 'Stamp version $GIT_HASH for publishing'"
echo "  3. Build PDF: cd crime-report/scripts && ./build_pdf.sh"
echo "  4. Publish to websites"
