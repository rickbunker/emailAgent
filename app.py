#!/usr/bin/env python3
"""
Startup script for the Email Agent Asset Management Web UI

Run this script to start the web interface for managing assets,
sender mappings, and document classification settings.
"""

# # Standard library imports
# Suppress HuggingFace tokenizers forking warning before any imports
import os
import warnings

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Suppress known qdrant-client SyntaxWarnings on Python 3.13+
warnings.filterwarnings(
    "ignore", message="invalid escape sequence", category=SyntaxWarning
)

# # Standard library imports
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))


def main():
    """Main function to run the web UI"""
    print("🌐 Email Agent Asset Management Web UI")
    print("=" * 50)
    print("Starting Flask development server...")
    print()
    print("📊 Dashboard:        http://localhost:5001")
    print("🏢 Assets:           http://localhost:5001/assets")
    print("📧 Sender Mappings:  http://localhost:5001/senders")
    print("🔧 API Health:       http://localhost:5001/api/health")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)

    # Import and run the Flask app
    try:
        # # Local application imports
        from web_ui.app import create_app

        app = create_app()
        app.run(debug=True, host="0.0.0.0", port=5001)
    except ImportError as e:
        print(f"❌ Failed to import Flask app: {e}")
        print("Make sure Flask is installed: pip install Flask>=2.3.0")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start web UI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
