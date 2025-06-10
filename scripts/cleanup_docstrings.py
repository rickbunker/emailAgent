#!/usr/bin/env python3
"""
Docstring and Author Cleanup Script

Systematically cleans up Python files by:
1. Updating author/license/copyright information
2. Removing boastful adjectives from docstrings
3. Maintaining consistent, documentation

Author: Rick Bunker, rbunker@inveniam.io
License: Private - Inveniam Capital Partners, LLC use only
Copyright: 2025 Inveniam Capital Partners, LLC and Rick Bunker
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
import re

# Target author/license format
TARGET_AUTHOR = "Author: Rick Bunker, rbunker@inveniam.io"
TARGET_LICENSE = "License: Private - Inveniam Capital Partners, LLC use only"
TARGET_COPYRIGHT = "Copyright: 2025 Inveniam Capital Partners, LLC and Rick Bunker"

def find_python_files(root_dir: str) -> List[Path]:
    """Find all Python files in the project."""
    python_files = []
    root_path = Path(root_dir)
    
    for file_path in root_path.rglob("*.py"):
        # Skip virtual environment and __pycache__ directories
        if any(part.startswith('.') or part == '__pycache__' for part in file_path.parts):
            continue
        python_files.append(file_path)
    
    return sorted(python_files)

def update_author_license(content: str) -> Tuple[str, bool]:
    """Update author/license/copyright information safely."""
    lines = content.splitlines()
    modified = False
    new_lines = []
    
    for i, line in enumerate(lines):
        # Check for exact author line patterns
        if line.strip() == "Author: Email Agent Development Team":
            new_lines.append(line.replace("Author: Email Agent Development Team", TARGET_AUTHOR))
            modified = True
        elif line.strip() == "License: Private - Asset Management Use Only":
            new_lines.append(line.replace("License: Private - Asset Management Use Only", TARGET_LICENSE))
            # Add copyright line after license if not already present
            if i + 1 < len(lines) and "Copyright:" not in lines[i + 1]:
                new_lines.append(TARGET_COPYRIGHT)
            modified = True
        elif line.strip().startswith("Copyright:"):
            new_lines.append(TARGET_COPYRIGHT)
            modified = True
        else:
            new_lines.append(line)
    
    return '\n'.join(new_lines), modified

def clean_boastful_language(content: str) -> Tuple[str, bool]:
    """Remove boastful adjectives safely, word by word."""
    original_content = content
    
    # Very simple word replacements (preserve all spacing and structure)
    replacements = {
        # Boastful adjectives - various patterns
        '': '',
        '': '', 
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        '': '',
        
        # More nuanced replacements
        'Complete': 'Complete',
        'complete': 'complete',
        'business': 'business',
        'business': 'business',
        'search': 'search',
        'knowledge': 'knowledge',
        'intelligence': 'intelligence',
        'email': 'email',
        'contact': 'contact',
        'memory': 'memory',
        'procedural': 'procedural',
        'workflow': 'workflow',
        'storage': 'storage',
        'retrieval': 'retrieval',
        'processing': 'processing',
        'learning': 'learning',
        'contact': 'contact',
        'merging': 'merging',
        'authentication': 'authentication',
        'styling': 'styling',
        'logging': 'logging',
        'user experience': 'user experience',
        'callback': 'callback',
        'API': 'API',
        'audit': 'audit',
        'credential': 'credential',
        'error handling': 'error handling',
        'validation': 'validation',
        'asset management': 'asset management',
        'contact': 'business contact',
        'relationship': 'business relationship',
        'environments': 'business environments',
        'search': 'search',
        'usage': 'usage',
        'email': 'email',
    }
    
    # Apply replacements very carefully
    for old_word, new_word in replacements.items():
        content = content.replace(old_word, new_word)
    
    return content, content != original_content

def process_file(file_path: Path, dry_run: bool = False) -> Dict[str, any]:
    """Process a single Python file."""
    result = {
        'file': str(file_path),
        'author_updated': False,
        'language_cleaned': False,
        'errors': [],
        'changes': []
    }
    
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        
        # Update author/license
        content, author_modified = update_author_license(content)
        if author_modified:
            result['author_updated'] = True
            result['changes'].append("Updated author/license/copyright")
        
        # Clean boastful language
        content, language_modified = clean_boastful_language(content)
        if language_modified:
            result['language_cleaned'] = True
            result['changes'].append("Removed boastful language")
        
        # Write back if changes were made and not dry run
        if (author_modified or language_modified) and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
    except Exception as e:
        result['errors'].append(str(e))
    
    return result

def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(description='Clean up Python docstrings and author info')
    parser.add_argument('--root', default='.', help='Root directory to scan (default: current directory)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    # Find all Python files
    print(f"🔍 Scanning for Python files in: {args.root}")
    python_files = find_python_files(args.root)
    print(f"📁 Found {len(python_files)} Python files")
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - No files will be modified")
    
    print("\n" + "="*60)
    
    # Process files
    results = []
    for file_path in python_files:
        result = process_file(file_path, dry_run=args.dry_run)
        results.append(result)
        
        if result['changes'] or result['errors'] or args.verbose:
            status = "✅" if result['changes'] and not result['errors'] else "❌" if result['errors'] else "⏭️"
            print(f"{status} {result['file']}")
            
            if result['changes']:
                for change in result['changes']:
                    print(f"    📝 {change}")
            
            if result['errors']:
                for error in result['errors']:
                    print(f"    ❌ Error: {error}")
            
            if args.verbose and not result['changes'] and not result['errors']:
                print(f"    ℹ️  No changes needed")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    total_files = len(results)
    author_updated = sum(1 for r in results if r['author_updated'])
    language_cleaned = sum(1 for r in results if r['language_cleaned'])
    errors = sum(1 for r in results if r['errors'])
    total_changes = sum(1 for r in results if r['changes'])
    
    print(f"📁 Files processed: {total_files}")
    print(f"✏️  Author/license updated: {author_updated}")
    print(f"🧹 Language cleaned: {language_cleaned}")
    print(f"✅ Total files changed: {total_changes}")
    print(f"❌ Files with errors: {errors}")
    
    if args.dry_run:
        print(f"\n🧪 This was a DRY RUN - run without --dry-run to apply changes")
    elif total_changes > 0:
        print(f"\n🎉 Successfully updated {total_changes} files!")
        print(f"💡 Review the changes and commit when ready")
    else:
        print(f"\n✨ All files are already clean!")

if __name__ == "__main__":
    main() 