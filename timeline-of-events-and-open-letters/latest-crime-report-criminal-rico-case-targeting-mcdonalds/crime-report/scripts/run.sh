#!/bin/bash
# Crime Report YAML Workflow Helper Script
# =========================================
#
# Usage:
#   ./run.sh generate        - Generate markdown from YAML sections
#   ./run.sh generate --dry-run  - Preview without writing
#   ./run.sh convert         - Convert markdown back to YAML (careful!)
#   ./run.sh status          - Show section status summary
#   ./run.sh draft <id>      - Mark a section as draft
#   ./run.sh publish <id>    - Mark a section as published
#   ./run.sh list-drafts     - List all draft sections

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"

# Activate virtual environment
activate_venv() {
    if [ -d "$VENV_DIR" ]; then
        source "$VENV_DIR/bin/activate"
    else
        echo "Error: Virtual environment not found at $VENV_DIR"
        echo "Create it with: python3 -m venv $VENV_DIR && source $VENV_DIR/bin/activate && pip install pyyaml"
        exit 1
    fi
}

# Generate markdown from YAML
generate() {
    activate_venv
    cd "$PROJECT_DIR"
    python3 scripts/yaml_to_md_generator.py "$@"
}

# Convert markdown to YAML
convert() {
    activate_venv
    cd "$PROJECT_DIR"
    python3 scripts/md_to_yaml_converter.py ../working_copy_index.en.md --output-dir sections/
}

# Show status summary
status() {
    echo "=== Section Status Summary ==="
    echo

    published=$(grep -c "status: published" "$PROJECT_DIR/meta.yaml" 2>/dev/null || echo "0")
    draft=$(grep -c "status: draft" "$PROJECT_DIR/meta.yaml" 2>/dev/null || echo "0")
    review=$(grep -c "status: review" "$PROJECT_DIR/meta.yaml" 2>/dev/null || echo "0")

    # Remove any whitespace/newlines
    published=${published//[^0-9]/}
    draft=${draft//[^0-9]/}
    review=${review//[^0-9]/}

    echo "Published: $published sections"
    echo "Draft:     $draft sections"
    echo "Review:    $review sections"
    echo
    total=$((published + draft + review))
    echo "Total:     $total sections"
}

# List draft sections
list_drafts() {
    echo "=== Draft Sections ==="
    grep -B2 "status: draft" "$PROJECT_DIR/meta.yaml" | grep "id:" | sed 's/.*- id: /  - /'
    echo
    echo "=== Review Sections ==="
    grep -B2 "status: review" "$PROJECT_DIR/meta.yaml" | grep "id:" | sed 's/.*- id: /  - /'
}

# Mark section as draft
mark_draft() {
    if [ -z "$1" ]; then
        echo "Usage: ./run.sh draft <section-id>"
        exit 1
    fi

    # This is a simple sed replacement - might need adjustment for complex cases
    sed -i '' "/id: $1$/,/status:/ s/status: .*/status: draft/" "$PROJECT_DIR/meta.yaml"
    echo "Marked section '$1' as draft"
}

# Mark section as published
mark_publish() {
    if [ -z "$1" ]; then
        echo "Usage: ./run.sh publish <section-id>"
        exit 1
    fi

    sed -i '' "/id: $1$/,/status:/ s/status: .*/status: published/" "$PROJECT_DIR/meta.yaml"
    echo "Marked section '$1' as published"
}

# Main command dispatcher
case "$1" in
    generate)
        shift
        generate "$@"
        ;;
    convert)
        convert
        ;;
    status)
        status
        ;;
    list-drafts)
        list_drafts
        ;;
    draft)
        mark_draft "$2"
        ;;
    publish)
        mark_publish "$2"
        ;;
    *)
        echo "Crime Report YAML Workflow"
        echo "=========================="
        echo
        echo "Usage: $0 <command> [options]"
        echo
        echo "Commands:"
        echo "  generate [--dry-run]   Generate markdown from YAML sections"
        echo "  convert                Convert markdown back to YAML (careful!)"
        echo "  status                 Show section status summary"
        echo "  list-drafts            List all draft/review sections"
        echo "  draft <id>             Mark a section as draft"
        echo "  publish <id>           Mark a section as published"
        echo
        echo "Examples:"
        echo "  $0 generate                    # Build the markdown file"
        echo "  $0 generate --dry-run          # Preview without writing"
        echo "  $0 draft IV-GG                 # Hide section IV-GG"
        echo "  $0 publish IV-GG               # Show section IV-GG"
        echo "  $0 list-drafts                 # See what's hidden"
        ;;
esac
