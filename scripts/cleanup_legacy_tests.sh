#!/usr/bin/env bash
# Cleanup script to remove legacy/obsolete test files
# Run: bash scripts/cleanup_legacy_tests.sh && git commit -m "Remove legacy test files"
# Then push normally.
set -euo pipefail

obsolete_tests=(
  "tests/simple_phase3_test.py"
  "tests/simple_validation_test.py"
  "tests/quick_validation_test.py"
  "tests/__pycache__"
)

echo "Removing obsolete tests..."
for path in "${obsolete_tests[@]}"; do
  if [ -e "$path" ]; then
    echo "  Deleting $path"
    git rm -rf "$path"
  else
    echo "  Skipped $path (not found)"
  fi
done

echo "All specified legacy test files have been removed."
echo "Next: review 'git status' and commit the deletions."
