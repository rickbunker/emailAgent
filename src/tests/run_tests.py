import asyncio
import argparse
from .test_memory import main

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run memory system tests")
    parser.add_argument(
        "--force-cleanup", 
        action="store_true",
        help="Force cleanup of collections without user confirmation"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    print("Starting memory system tests...")
    asyncio.run(main(force_cleanup=args.force_cleanup))
    print("\nAll tests completed!") 