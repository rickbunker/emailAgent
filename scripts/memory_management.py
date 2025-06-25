#!/usr/bin/env python3
"""
Memory Management CLI Tool for Email Agent

Provides command-line access to memory backup, restore, export, and reset operations.
"""

# Standard library imports
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Local application imports must come after sys.path modification
# ruff: noqa: E402
from src.memory.simple_memory import (
    MEMORY_DATA_DIR,
    create_memory_backup,
    export_all_memory_to_github_format,
    export_episodic_memory_to_json,
    reset_all_memory_to_baseline,
    restore_memory_from_backup,
)
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


def backup_memory(args):
    """Create a backup of all memory systems."""
    backup_name = args.name or datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"Creating memory backup: {backup_name}")
    try:
        result = create_memory_backup(backup_name)
        print("✅ Backup created successfully!")
        print("\nBackup files:")
        for memory_type, path in result.items():
            print(f"  {memory_type}: {path}")

        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False


def restore_memory(args):
    """Restore memory systems from a backup."""
    backup_name = args.backup_name

    if not backup_name:
        # List available backups
        backups_dir = MEMORY_DATA_DIR / "backups"
        if backups_dir.exists():
            backups = [d.name for d in backups_dir.iterdir() if d.is_dir()]
            if backups:
                print("Available backups:")
                for backup in sorted(backups):
                    print(f"  {backup}")
            else:
                print("No backups found.")
        else:
            print("No backups directory found.")
        return

    print(f"Restoring memory from backup: {backup_name}")
    try:
        result = restore_memory_from_backup(backup_name)
        print("✅ Restore completed!")
        print("\nRestore results:")
        for memory_type, success in result.items():
            status = "✅" if success else "❌"
            print(f"  {memory_type}: {status}")

        return all(result.values())
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False


def export_memory(args):
    """Export memory systems for GitHub."""
    print("Exporting memory systems for GitHub...")
    try:
        result = export_all_memory_to_github_format()
        print("✅ Export completed!")
        print("\nExported files:")
        for memory_type, path in result.items():
            print(f"  {memory_type}: {path}")

        # Also export episodic memory separately if requested
        if args.episodic_json:
            episodic_data = export_episodic_memory_to_json()
            export_path = MEMORY_DATA_DIR / "episodic_memory_standalone.json"
            with open(export_path, "w") as f:
                json.dump(episodic_data, f, indent=2, sort_keys=True)
            print(f"  episodic_standalone: {export_path}")

        return True
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False


def reset_memory(args):
    """Reset memory systems to baseline."""
    if not args.confirm:
        response = input(
            "⚠️  This will reset ALL memory systems to baseline. Continue? (y/N): "
        )
        if response.lower() != "y":
            print("Reset cancelled.")
            return False

    print("Resetting memory systems to baseline...")
    try:
        result = reset_all_memory_to_baseline()
        print("✅ Reset completed!")
        print("\nReset results:")
        for memory_type, count in result.items():
            print(f"  {memory_type}: {count} items")

        total_items = sum(result.values())
        print(f"\nTotal items reset: {total_items}")
        return True
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False


def status_memory(args):
    """Show memory system status."""
    print("Memory System Status")
    print("=" * 50)

    # Check file existence and sizes
    memory_files = [
        ("Semantic Memory", "semantic_memory.json"),
        ("Semantic Baseline", "semantic_memory_baseline.json"),
        ("Procedural Memory", "procedural_memory.json"),
        ("Procedural Baseline", "procedural_memory_baseline.json"),
        ("Episodic Database", "episodic_memory.db"),
        ("Episodic Baseline", "episodic_memory_baseline.json"),
        ("Memory Status", "memory_status.json"),
        ("Episodic Export", "episodic_memory_export.json"),
    ]

    for name, filename in memory_files:
        file_path = MEMORY_DATA_DIR / filename
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            modified = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(
                f"✅ {name:<20}: {size_kb:6.1f}KB (modified: {modified.strftime('%Y-%m-%d %H:%M')})"
            )
        else:
            print(f"❌ {name:<20}: Not found")

    # Check backups
    backups_dir = MEMORY_DATA_DIR / "backups"
    if backups_dir.exists():
        backups = [d for d in backups_dir.iterdir() if d.is_dir()]
        print(f"\n📦 Backups: {len(backups)} available")
        for backup in sorted(backups)[-5:]:  # Show last 5 backups
            print(f"   {backup.name}")
    else:
        print("\n📦 Backups: No backup directory found")

    # Load and show status from memory_status.json if available
    status_file = MEMORY_DATA_DIR / "memory_status.json"
    if status_file.exists():
        try:
            status_data = json.loads(status_file.read_text())
            print(
                f"\n📊 System Status (as of {status_data.get('last_export', 'unknown')}):"
            )
            for name, info in status_data.get("memory_systems", {}).items():
                if "item_count" in info:
                    print(f"   {name.capitalize()}: {info['item_count']} items")
                elif "rule_count" in info:
                    print(f"   {name.capitalize()}: {info['rule_count']} rules")
                elif "record_count" in info:
                    print(f"   {name.capitalize()}: {info['record_count']} records")
        except Exception as e:
            print(f"\n⚠️  Could not read status file: {e}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Email Agent Memory Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a memory backup")
    backup_parser.add_argument("--name", help="Backup name (default: timestamp)")
    backup_parser.set_defaults(func=backup_memory)

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument(
        "backup_name", nargs="?", help="Backup name to restore (omit to list available)"
    )
    restore_parser.set_defaults(func=restore_memory)

    # Export command
    export_parser = subparsers.add_parser("export", help="Export memory for GitHub")
    export_parser.add_argument(
        "--episodic-json",
        action="store_true",
        help="Also create standalone episodic JSON export",
    )
    export_parser.set_defaults(func=export_memory)

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset memory to baseline")
    reset_parser.add_argument(
        "--confirm", action="store_true", help="Skip confirmation prompt"
    )
    reset_parser.set_defaults(func=reset_memory)

    # Status command
    status_parser = subparsers.add_parser("status", help="Show memory system status")
    status_parser.set_defaults(func=status_memory)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Ensure memory directory exists
    MEMORY_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Run the command
    try:
        success = args.func(args)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
