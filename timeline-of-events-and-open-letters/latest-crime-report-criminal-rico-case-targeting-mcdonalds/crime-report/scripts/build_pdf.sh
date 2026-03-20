#!/bin/bash
#
# Build PDF from index.en.md with page-bottom footnotes
#
# Usage:
#   ./build_pdf.sh [OPTIONS]
#
# Run ./build_pdf.sh --help to see all available options.
#

set -e

# Default values
LINE_SPACING="1.15"
PARA_SPACING="0.5em"
GREEN_COLOR="ForestGreen"
RED_COLOR="red"
PARA_NUM_SIZE="normalsize"

# Get git hash for version tracking
get_git_version() {
    # Navigate to the content directory (where .git should be)
    local CONTENT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
    cd "$CONTENT_DIR"

    if git rev-parse --git-dir > /dev/null 2>&1; then
        local GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "no-commits")
        # Check for uncommitted changes
        if ! git diff-index --quiet HEAD -- 2>/dev/null; then
            GIT_HASH="${GIT_HASH}-dirty"
        fi
        echo "$GIT_HASH"
    else
        echo "initial"
    fi
}

GIT_HASH=$(get_git_version)
VERSION="version\\#${GIT_HASH}"

# Help function
show_help() {
    cat << 'EOF'
Usage: ./build_pdf.sh [OPTIONS]

Build a PDF from index.en.md with customizable formatting.

OPTIONS:
    --help                      Show this help message and exit

    --line-spacing=VALUE        Space between lines within a paragraph
                                Default: 1.5
                                Examples: 1.0 (single), 1.5 (one-and-half), 2.0 (double)

    --para-spacing=VALUE        Space between paragraphs
                                Default: 0.5em
                                Examples: 0em (tight), 1em (more space), 1.5em (lots of space)

    --green-color=VALUE         Color for green text (darker = more readable)
                                Default: ForestGreen
                                Examples: green, OliveGreen, DarkGreen, ForestGreen, Aquamarine

    --red-color=VALUE           Color for red text
                                Default: red
                                Examples: red, Maroon, BrickRed, Crimson

    --para-num-size=VALUE       Font size for (version#initial)(N) paragraph numbers
                                Default: normalsize (same as body text)
                                Options: tiny, scriptsize, footnotesize, small, normalsize

EXAMPLES:
    # Build with default settings
    ./build_pdf.sh

    # Build with more line spacing
    ./build_pdf.sh --line-spacing=1.5

    # Build with more paragraph spacing and darker green
    ./build_pdf.sh --para-spacing=1em --green-color=DarkGreen

    # Build with smaller paragraph numbers
    ./build_pdf.sh --para-num-size=footnotesize

OUTPUT:
    crime-report-draft-33.pdf (in parent directory alongside index.en.md)

FOOTER:
    Bottom-left: version#<git-hash> -- Built: YYYY-MM-DD HH:MM:SS TZ
    Bottom-right: Page X of Y

VERSION:
    The version is automatically derived from the git commit hash.
    - If git repo exists: version#abc1234 (7-character short hash)
    - If uncommitted changes: version#abc1234-dirty
    - If no git repo: version#initial
EOF
}

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        --help|-h)
            show_help
            exit 0
            ;;
        --line-spacing=*)
            LINE_SPACING="${arg#*=}"
            ;;
        --para-spacing=*)
            PARA_SPACING="${arg#*=}"
            ;;
        --green-color=*)
            GREEN_COLOR="${arg#*=}"
            ;;
        --red-color=*)
            RED_COLOR="${arg#*=}"
            ;;
        --para-num-size=*)
            PARA_NUM_SIZE="${arg#*=}"
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Run ./build_pdf.sh --help for usage information."
            exit 1
            ;;
    esac
done

# Get script directory and navigate to content directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRIME_REPORT_DIR="$(dirname "$SCRIPT_DIR")"
CONTENT_DIR="$(dirname "$CRIME_REPORT_DIR")"

# File paths
INPUT_FILE="$CONTENT_DIR/index.en.md"
TEMP_FILE="$CRIME_REPORT_DIR/temp_preprocessed.md"
OUTPUT_PDF="$CONTENT_DIR/crime-report-draft-33.pdf"
TEMPLATE_FILE="$SCRIPT_DIR/pdf-template.latex"

# Get current date, time, and timezone
BUILD_DATE=$(date "+%Y-%m-%d")
BUILD_TIME=$(date "+%H:%M:%S")
TIMEZONE=$(date "+%Z")

echo "=== Building PDF from index.en.md ==="
echo "Input:  $INPUT_FILE"
echo "Output: $OUTPUT_PDF"
echo ""
echo "Settings:"
echo "  Line spacing:     $LINE_SPACING"
echo "  Para spacing:     $PARA_SPACING"
echo "  Green color:      $GREEN_COLOR"
echo "  Red color:        $RED_COLOR"
echo "  Para num size:    $PARA_NUM_SIZE"
echo "  Version:          $VERSION"
echo "  Build time:       $BUILD_DATE $BUILD_TIME $TIMEZONE"
echo ""

# Step 1: Preprocess the markdown
echo "1. Preprocessing markdown (removing Hugo syntax, converting styles)..."
python3 "$SCRIPT_DIR/preprocess_for_pdf.py" "$INPUT_FILE" "$TEMP_FILE" \
    --green-color="$GREEN_COLOR" \
    --red-color="$RED_COLOR" \
    --para-num-size="$PARA_NUM_SIZE"

# Step 2: Change to content directory so relative image paths work
cd "$CONTENT_DIR"

# Step 3: Generate PDF with Pandoc + XeLaTeX
echo "2. Generating PDF with Pandoc + XeLaTeX..."
pandoc "crime-report/temp_preprocessed.md" \
    -o "$OUTPUT_PDF" \
    --pdf-engine=xelatex \
    --template="$TEMPLATE_FILE" \
    --toc \
    --toc-depth=3 \
    -V fontsize=12pt \
    -V documentclass=article \
    -V linkcolor=blue \
    -V urlcolor=blue \
    -V linestretch="$LINE_SPACING" \
    -V paraspacing="$PARA_SPACING" \
    -V version="$VERSION" \
    -V builddate="$BUILD_DATE" \
    -V buildtime="$BUILD_TIME" \
    -V timezone="$TIMEZONE" \
    --syntax-highlighting=tango \
    --fail-if-warnings=false \
    2>&1 | grep -v "Could not fetch resource" || true

# Step 4: Cleanup temporary file
echo "3. Cleaning up..."
rm -f "$TEMP_FILE"

# Step 5: Report success
echo ""
echo "=== PDF generation complete ==="
echo "Output: $OUTPUT_PDF"

# Show file size and page count
if [ -f "$OUTPUT_PDF" ]; then
    SIZE=$(ls -lh "$OUTPUT_PDF" | awk '{print $5}')
    echo "Size:   $SIZE"

    # Try to get page count
    if command -v pdfinfo &> /dev/null; then
        PAGES=$(pdfinfo "$OUTPUT_PDF" 2>/dev/null | grep "Pages:" | awk '{print $2}')
        echo "Pages:  $PAGES"
    fi
fi
