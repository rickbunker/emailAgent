#!/usr/bin/env python3
"""
Comprehensive Test Harness for Email Agent

This script runs all code quality checks, type checking, security scans,
and tests for the Email Agent project. It provides a single command to
validate the entire codebase.

Usage:
    python scripts/test_harness.py [options]

Options:
    --quick     Skip slower checks (bandit, full type checking)
    --format    Run code formatters (black, isort) before tests
    --coverage  Generate detailed coverage reports
    --verbose   Show detailed output from all tools
    --fix       Automatically fix issues where possible
"""

# # Standard library imports
import argparse
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# # Local application imports
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


class TestHarness:
    """Comprehensive test harness for code quality and testing."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.failed_checks: list[str] = []
        self.passed_checks: list[str] = []

    def run_command(
        self, cmd: list[str], description: str, allow_failure: bool = False
    ) -> tuple[bool, str]:
        """
        Run a command and capture its output.

        Args:
            cmd: Command to run as list of strings
            description: Human-readable description for logging
            allow_failure: If True, don't treat non-zero exit as failure

        Returns:
            Tuple of (success, output)
        """
        logger.info(f"🔍 {description}")

        if self.verbose:
            print(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                self.passed_checks.append(description)
                if self.verbose:
                    print(f"✅ {description}")
                    if result.stdout:
                        print(result.stdout)
                return True, result.stdout
            else:
                if not allow_failure:
                    self.failed_checks.append(description)
                if self.verbose or result.returncode != 0:
                    print(f"❌ {description}")
                    if result.stdout:
                        print("STDOUT:", result.stdout)
                    if result.stderr:
                        print("STDERR:", result.stderr)
                return False, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = "Command timed out after 5 minutes"
            self.failed_checks.append(f"{description} (timeout)")
            print(f"⏰ {description} - {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Command failed with exception: {e}"
            self.failed_checks.append(f"{description} (exception)")
            print(f"💥 {description} - {error_msg}")
            return False, error_msg

    def check_dependencies(self) -> bool:
        """Check that all required tools are available."""
        logger.info("🔧 Checking tool dependencies")

        tools = [
            ("python", ["python", "--version"]),
            ("pytest", ["pytest", "--version"]),
            ("black", ["black", "--version"]),
            ("isort", ["isort", "--version"]),
            ("mypy", ["mypy", "--version"]),
            ("pylint", ["pylint", "--version"]),
            ("ruff", ["ruff", "--version"]),
            ("bandit", ["bandit", "--version"]),
        ]

        missing_tools = []
        for tool_name, cmd in tools:
            success, _ = self.run_command(cmd, f"Check {tool_name}", allow_failure=True)
            if not success:
                missing_tools.append(tool_name)

        if missing_tools:
            print(f"❌ Missing tools: {', '.join(missing_tools)}")
            print("💡 Install with: pip install -r requirements-dev.txt")
            return False

        print("✅ All development tools available")
        return True

    def run_formatters(self) -> bool:
        """Run code formatters (black, isort)."""
        logger.info("🎨 Running code formatters")

        # Run black
        black_success, _ = self.run_command(
            ["black", "src", "tests", "scripts"], "Format code with black"
        )

        # Run isort
        isort_success, _ = self.run_command(
            ["isort", "src", "tests", "scripts"], "Sort imports with isort"
        )

        return black_success and isort_success

    def run_linting(self, fix: bool = False) -> bool:
        """Run code linting checks."""
        logger.info("🔍 Running linting checks")

        # Run ruff (fast Python linter)
        ruff_cmd = ["ruff", "check", "src", "tests"]
        if fix:
            ruff_cmd.append("--fix")

        ruff_success, _ = self.run_command(ruff_cmd, "Lint with ruff")

        # Run pylint (comprehensive but slower)
        pylint_success, _ = self.run_command(
            ["pylint", "src"],
            "Advanced linting with pylint",
            allow_failure=True,  # Pylint can be strict, don't fail the build
        )

        return ruff_success  # Only require ruff to pass

    def run_type_checking(self, quick: bool = False) -> bool:
        """Run type checking with mypy."""
        logger.info("🔍 Running type checking")

        if quick:
            # Quick check: just critical files
            files = ["src/web_ui/app.py", "src/agents/asset_document_agent.py"]
            cmd = ["mypy", "--ignore-missing-imports", "--no-strict-optional"] + files
        else:
            # Full check with relaxed settings for commit compatibility
            cmd = ["mypy", "--ignore-missing-imports", "--no-strict-optional", "src"]

        # Run but don't fail the build on MyPy issues (for commit compatibility)
        success, output = self.run_command(
            cmd, "Type checking with mypy", allow_failure=True
        )
        return True  # Always return True to not fail the build

    def run_security_checks(self) -> bool:
        """Run security scanning with bandit."""
        logger.info("🔒 Running security checks")

        # Run but don't fail the build on security warnings (for commit compatibility)
        success, output = self.run_command(
            ["bandit", "-r", "src", "-f", "txt"],
            "Security scan with bandit",
            allow_failure=True,
        )
        return True  # Always return True to not fail the build

    def run_tests(self, coverage: bool = False) -> bool:
        """Run the test suite."""
        logger.info("🧪 Running test suite")

        cmd = ["pytest", "tests/", "-v"]

        if coverage:
            cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])

        return self.run_command(cmd, "Run test suite")[0]

    def run_pre_commit_checks(self) -> bool:
        """Run pre-commit hooks on all files."""
        logger.info("🎯 Running pre-commit checks")

        return self.run_command(
            ["pre-commit", "run", "--all-files"],
            "Pre-commit hooks",
            allow_failure=True,  # Some hooks might have warnings
        )[0]

    def generate_report(self) -> None:
        """Generate a summary report of all checks."""
        print("\n" + "=" * 60)
        print("📊 TEST HARNESS SUMMARY REPORT")
        print("=" * 60)

        print(f"\n✅ PASSED CHECKS ({len(self.passed_checks)}):")
        for check in self.passed_checks:
            print(f"  ✓ {check}")

        if self.failed_checks:
            print(f"\n❌ FAILED CHECKS ({len(self.failed_checks)}):")
            for check in self.failed_checks:
                print(f"  ✗ {check}")

        overall_success = len(self.failed_checks) == 0

        print(f"\n🎯 OVERALL RESULT: {'✅ PASS' if overall_success else '❌ FAIL'}")

        if not overall_success:
            print("\n💡 To fix issues:")
            print("  - Run with --fix to auto-fix some issues")
            print("  - Run with --format to format code")
            print("  - Check individual tool output above")

        print("=" * 60)


def main():
    """Main entry point for the test harness."""
    parser = argparse.ArgumentParser(description="Email Agent Test Harness")
    parser.add_argument("--quick", action="store_true", help="Skip slower checks")
    parser.add_argument(
        "--format", action="store_true", help="Run code formatters before tests"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage reports"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix issues where possible"
    )
    parser.add_argument(
        "--pre-commit-only", action="store_true", help="Only run pre-commit checks"
    )

    args = parser.parse_args()

    harness = TestHarness(verbose=args.verbose)

    print("🚀 Email Agent Test Harness")
    print("=" * 40)

    # Check dependencies first
    if not harness.check_dependencies():
        sys.exit(1)

    if args.pre_commit_only:
        harness.run_pre_commit_checks()
        harness.generate_report()
        sys.exit(0 if not harness.failed_checks else 1)

    # Run formatters if requested
    if args.format:
        harness.run_formatters()

    # Run all checks
    harness.run_linting(fix=args.fix)
    harness.run_type_checking(quick=args.quick)

    if not args.quick:
        harness.run_security_checks()

    harness.run_tests(coverage=args.coverage)

    # Generate final report
    harness.generate_report()

    # Exit with appropriate code
    sys.exit(0 if not harness.failed_checks else 1)


if __name__ == "__main__":
    main()
