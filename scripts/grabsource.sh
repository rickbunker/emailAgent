#!/bin/bash
#
# Source Code Extraction Utility
#
# Extracts and packages source code from the Email Agent project
# for analysis, backup, or distribution purposes.
#
# Usage:
#   ./scripts/grabsource.sh [options]
#
# Options:
#   --output DIR     Output directory (default: ./source_export)
#   --format FORMAT  Export format: tar|zip|copy (default: tar)
#   --include-docs   Include documentation files
#   --include-tests  Include test files
#   --include-config Include configuration files
#   --exclude-logs   Exclude log files (default)
#   --help          Show this help message

set -e  # Exit on any error

# Default configuration
OUTPUT_DIR="./source_export"
FORMAT="tar"
INCLUDE_DOCS=false
INCLUDE_TESTS=false
INCLUDE_CONFIG=false
EXCLUDE_LOGS=true
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to show help
show_help() {
    cat << EOF
🛠️  Email Agent Source Code Extraction Utility

USAGE:
    ./scripts/grabsource.sh [OPTIONS]

OPTIONS:
    --output DIR        Output directory (default: ./source_export)
    --format FORMAT     Export format: tar|zip|copy (default: tar)
    --include-docs      Include documentation files
    --include-tests     Include test files
    --include-config    Include configuration files
    --exclude-logs      Exclude log files (default: enabled)
    --help             Show this help message

EXAMPLES:
    # Basic source export
    ./scripts/grabsource.sh

    # Full export with docs and tests
    ./scripts/grabsource.sh --include-docs --include-tests --format zip

    # Copy source to specific directory
    ./scripts/grabsource.sh --output /tmp/emailagent_src --format copy

DESCRIPTION:
    This script extracts the Email Agent source code, filtering out
    unnecessary files like logs, caches, and build artifacts. It's
    useful for creating clean source distributions or backups.

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --include-docs)
            INCLUDE_DOCS=true
            shift
            ;;
        --include-tests)
            INCLUDE_TESTS=true
            shift
            ;;
        --include-config)
            INCLUDE_CONFIG=true
            shift
            ;;
        --exclude-logs)
            EXCLUDE_LOGS=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate format
if [[ ! "$FORMAT" =~ ^(tar|zip|copy)$ ]]; then
    print_error "Invalid format: $FORMAT. Must be tar, zip, or copy"
    exit 1
fi

print_info "Email Agent Source Code Extraction"
echo "=================================="

# Change to project root
cd "$PROJECT_ROOT"

print_info "Project root: $PROJECT_ROOT"
print_info "Output: $OUTPUT_DIR"
print_info "Format: $FORMAT"

# Create temporary directory for staging
TEMP_DIR=$(mktemp -d)
STAGE_DIR="$TEMP_DIR/emailAgent"

print_info "Staging directory: $STAGE_DIR"

# Create staging directory
mkdir -p "$STAGE_DIR"

# Function to copy files with exclusions
copy_source_files() {
    print_info "Copying core source files..."

    # Core source files
    rsync -av --progress \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.pyo' \
        --exclude='.pytest_cache' \
        --exclude='.mypy_cache' \
        --exclude='.ruff_cache' \
        --exclude='htmlcov' \
        --exclude='.coverage' \
        --exclude='*.egg-info' \
        --exclude='build/' \
        --exclude='dist/' \
        src/ "$STAGE_DIR/src/"

    # Main application files
    cp app.py "$STAGE_DIR/" 2>/dev/null || true
    cp README.md "$STAGE_DIR/" 2>/dev/null || true
    cp requirements.txt "$STAGE_DIR/" 2>/dev/null || true
    cp requirements-dev.txt "$STAGE_DIR/" 2>/dev/null || true
    cp pyproject.toml "$STAGE_DIR/" 2>/dev/null || true
    cp Makefile "$STAGE_DIR/" 2>/dev/null || true
    cp mypy.ini "$STAGE_DIR/" 2>/dev/null || true

    # Scripts directory
    mkdir -p "$STAGE_DIR/scripts"
    cp scripts/*.py "$STAGE_DIR/scripts/" 2>/dev/null || true
    cp scripts/*.sh "$STAGE_DIR/scripts/" 2>/dev/null || true
    cp scripts/README.md "$STAGE_DIR/scripts/" 2>/dev/null || true

    print_success "Core source files copied"
}

# Function to copy documentation
copy_docs() {
    if [[ "$INCLUDE_DOCS" == true ]]; then
        print_info "Copying documentation..."

        if [[ -d "docs" ]]; then
            rsync -av docs/ "$STAGE_DIR/docs/"
        fi

        if [[ -d "examples" ]]; then
            rsync -av examples/ "$STAGE_DIR/examples/"
        fi

        if [[ -d "knowledge" ]]; then
            rsync -av knowledge/ "$STAGE_DIR/knowledge/"
        fi

        print_success "Documentation copied"
    else
        print_warning "Documentation excluded (use --include-docs to include)"
    fi
}

# Function to copy tests
copy_tests() {
    if [[ "$INCLUDE_TESTS" == true ]]; then
        print_info "Copying tests..."

        if [[ -d "tests" ]]; then
            rsync -av \
                --exclude='__pycache__' \
                --exclude='*.pyc' \
                --exclude='.pytest_cache' \
                tests/ "$STAGE_DIR/tests/"
        fi

        print_success "Tests copied"
    else
        print_warning "Tests excluded (use --include-tests to include)"
    fi
}

# Function to copy configuration
copy_config() {
    if [[ "$INCLUDE_CONFIG" == true ]]; then
        print_info "Copying configuration files..."

        if [[ -d "config" ]]; then
            # Copy config but exclude sensitive files
            rsync -av \
                --exclude='*.env' \
                --exclude='*secret*' \
                --exclude='*private*' \
                config/ "$STAGE_DIR/config/"
        fi

        # Copy environment template if it exists
        cp .env.template "$STAGE_DIR/" 2>/dev/null || true

        print_success "Configuration files copied"
    else
        print_warning "Configuration excluded (use --include-config to include)"
    fi
}

# Function to create archive
create_archive() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local base_name="emailAgent_source_$timestamp"

    # Ensure output directory exists
    mkdir -p "$(dirname "$OUTPUT_DIR")"

    case $FORMAT in
        tar)
            local archive_path="$OUTPUT_DIR/${base_name}.tar.gz"
            print_info "Creating tar archive: $archive_path"

            tar -czf "$archive_path" -C "$TEMP_DIR" emailAgent
            print_success "Archive created: $archive_path"
            ;;

        zip)
            local archive_path="$OUTPUT_DIR/${base_name}.zip"
            print_info "Creating zip archive: $archive_path"

            cd "$TEMP_DIR"
            zip -r "$archive_path" emailAgent/
            cd "$PROJECT_ROOT"
            print_success "Archive created: $archive_path"
            ;;

        copy)
            print_info "Copying to: $OUTPUT_DIR"

            # Remove existing directory if it exists
            if [[ -d "$OUTPUT_DIR" ]]; then
                rm -rf "$OUTPUT_DIR"
            fi

            cp -r "$STAGE_DIR" "$OUTPUT_DIR"
            print_success "Source copied to: $OUTPUT_DIR"
            ;;
    esac
}

# Function to generate manifest
generate_manifest() {
    local manifest_file="$STAGE_DIR/SOURCE_MANIFEST.txt"

    print_info "Generating source manifest..."

    cat > "$manifest_file" << EOF
Email Agent Source Code Export
==============================

Export Date: $(date)
Export Tool: grabsource.sh
Project Root: $PROJECT_ROOT

Configuration:
- Include Documentation: $INCLUDE_DOCS
- Include Tests: $INCLUDE_TESTS
- Include Configuration: $INCLUDE_CONFIG
- Exclude Logs: $EXCLUDE_LOGS

File Structure:
EOF

    # Add file tree to manifest
    cd "$STAGE_DIR"
    find . -type f | sort >> "$manifest_file"
    cd "$PROJECT_ROOT"

    print_success "Manifest generated: SOURCE_MANIFEST.txt"
}

# Function to cleanup
cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
        print_info "Temporary files cleaned up"
    fi
}

# Set up cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    print_info "Starting source extraction..."

    # Copy files based on options
    copy_source_files
    copy_docs
    copy_tests
    copy_config

    # Generate manifest
    generate_manifest

    # Show summary
    echo
    print_info "Source Summary:"
    echo "  📁 Total files: $(find "$STAGE_DIR" -type f | wc -l)"
    echo "  📊 Total size: $(du -sh "$STAGE_DIR" | cut -f1)"

    # Create final output
    create_archive

    print_success "Source extraction completed successfully!"
}

# Run main function
main
