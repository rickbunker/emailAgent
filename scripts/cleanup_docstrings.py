#!/usr/bin/env python3
"""
Cleanup script to:
1. Remove boastful adjectives from docstrings, comments, and documentation
2. Update author/license information to proper format
3. Maintaining consistent documentation across Python and Markdown files
"""

import os
import re
from pathlib import Path

def cleanup_file(file_path):
    """Clean up a single Python or Markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
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
            'document': 'document',
            'email': 'email',
            'asset': 'asset',
            'portfolio': 'portfolio',
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
            'documentation': 'documentation',
            'architecture': 'architecture',
            'search': 'search',
            'usage': 'usage',
            'analytics': 'analytics',
            'security': 'security',
            'permissions': 'permissions',
            'detection': 'detection',
            'configuration': 'configuration',
            'features': 'features',
            'email': 'email',
            'spam': 'spam',
            'filtering': 'filtering',
            'search': 'search',
            
            # Markdown-specific patterns
            '**': '**',
            '**': '**',
            '**': '**',
            '**': '**',
            '**Complete': '**Complete',
            '**': '**',
            '- **Complete': '- **Complete',
            '- **': '- **',
            '- **': '- **',
            '- **': '- **',
            '- **': '- **',
        }
        
        # Apply simple string replacements
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        # Only update author/license/copyright for Python files
        if file_path.suffix == '.py':
            # Update author/license information - look for existing patterns
            author_patterns = [
                (r'Author: Rick Bunker, rbunker@inveniam.io
                (r'@author Rick Bunker, rbunker@inveniam.io
                (r'Created by: Rick Bunker, rbunker@inveniam.io
            ]
            
            license_patterns = [
                (r'License: Private - Inveniam Capital Partners, LLC use only
                (r'@license Private - Inveniam Capital Partners, LLC use only
            ]
            
            copyright_patterns = [
                (r'Copyright: 2025 Inveniam Capital Partners, LLC and Rick Bunker
                (r'@copyright 2025 Inveniam Capital Partners, LLC
                (r'\(c\).*\d{4}.*', '(c) 2025 Inveniam Capital Partners, LLC and Rick Bunker
            ]
            
            # Apply author/license/copyright updates
            for pattern, replacement in author_patterns + license_patterns + copyright_patterns:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Updated"
        else:
            return True, "No changes needed"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Run cleanup on all Python and Markdown files."""
    # Find all Python and Markdown files
    python_files = list(Path('.').rglob('*.py'))
    markdown_files = list(Path('.').rglob('*.md'))
    all_files = python_files + markdown_files
    
    total_files = len(all_files)
    
    print(f"🔍 Found {len(python_files)} Python files and {len(markdown_files)} Markdown files")
    print(f"📄 Total files to process: {total_files}")
    print("=" * 60)
    
    success_count = 0
    updated_count = 0
    error_count = 0
    
    for file_path in all_files:
        success, message = cleanup_file(file_path)
        
        file_type = "🐍" if file_path.suffix == '.py' else "📝"
        relative_path = file_path.relative_to('.')
        
        if success:
            success_count += 1
            if "Updated" in message:
                updated_count += 1
                print(f"✅ {file_type} {relative_path}: {message}")
            else:
                print(f"⚪ {file_type} {relative_path}: {message}")
        else:
            error_count += 1
            print(f"❌ {file_type} {relative_path}: {message}")
    
    print("=" * 60)
    print(f"📊 SUMMARY:")
    print(f"   Total files processed: {total_files}")
    print(f"   🐍 Python files: {len(python_files)}")
    print(f"   📝 Markdown files: {len(markdown_files)}")
    print(f"   ✅ Successful: {success_count}")
    print(f"   📝 Updated: {updated_count}")
    print(f"   ❌ Errors: {error_count}")
    
    if error_count == 0:
        print("\n🎉 All files processed successfully!")
    else:
        print(f"\n⚠️  {error_count} files had errors - please check manually")

if __name__ == "__main__":
    main() 