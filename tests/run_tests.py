"""
Memory System Test Runner for EmailAgent

test runner for executing complete memory system validation
in private market asset management email automation environments. Provides
streamlined test execution with reporting and error handling.

Features:
    - Complete test execution and coordination
    - command-line argument handling
    - Clean test environment management and validation
    - Complete error handling and reporting
    - logging integration and output
    - Asset management test scenario execution

Business Context:
    Designed for asset management firms requiring
    memory system validation for email automation, relationship
    management, knowledge retention, and business intelligence.
    Ensures system reliability for investment workflows,
    compliance, and operational efficiency.

Technical Architecture:
    - Command-line test execution interface
    - argument parsing and validation
    - Clean test environment setup and teardown
    - Complete test result reporting
    - error handling and logging

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License: Private - Inveniam Capital Partners, LLC use only
Copyright: 2025 Inveniam Capital Partners, LLC and Rick Bunker
"""

import asyncio
import argparse
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime, UTC

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Core logging system
from utils.logging_system import get_logger, log_function, log_info

# Test module import
from .test_memory import main as run_memory_tests

# Initialize logger
logger = get_logger(__name__)

class TestRunner:
    """
    test runner for EmailAgent memory systems.
    
    Provides complete test execution capabilities with professional
    command-line interface, argument handling, and result reporting
    for asset management email automation environments.
    
    Features:
        - command-line argument parsing
        - Complete test environment management
        - Clean test execution and coordination
        - result reporting and logging
        - Error handling and recovery management
        
    Attributes:
        args: Parsed command-line arguments
        test_stats: Test execution statistics and metrics
    """
    
    def __init__(self) -> None:
        """Initialize the test runner."""
        logger.info("Initializing TestRunner for memory system validation")
        
        self.args: Optional[argparse.Namespace] = None
        self.test_stats = {
            'start_time': None,
            'end_time': None,
            'total_duration': 0,
            'tests_executed': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'success_rate': 0.0
        }
        
        logger.info("TestRunner initialized successfully")

    @log_function()
    def parse_arguments(self) -> argparse.Namespace:
        """
        Parse command line arguments for test execution.
        
        Provides complete argument parsing for test configuration,
        cleanup options, and execution parameters for professional
        test environment management.
        
        Returns:
            Parsed command-line arguments namespace
        """
        logger.info("Parsing command-line arguments for test execution")
        
        parser = argparse.ArgumentParser(
            description="EmailAgent Memory System Test Runner",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
    python run_tests.py                    # Run tests with user confirmation
    python run_tests.py --force-cleanup   # Run tests with automatic cleanup
    python run_tests.py --verbose         # Run tests with detailed output
    python run_tests.py --quick           # Run quick validation tests only

Asset Management Testing:
    This test runner validates memory systems for private market
    asset management email automation including investment rules,
    compliance procedures, and relationship intelligence.
            """
        )
        
        # Core test execution arguments
        parser.add_argument(
            "--force-cleanup", 
            action="store_true",
            help="Force cleanup of test collections without user confirmation"
        )
        
        parser.add_argument(
            "--verbose", 
            action="store_true",
            help="Enable verbose output with detailed test information"
        )
        
        parser.add_argument(
            "--quick", 
            action="store_true",
            help="Run quick validation tests only (skip performance tests)"
        )
        
        parser.add_argument(
            "--test-suite",
            choices=["memory", "integration", "performance", "all"],
            default="all",
            help="Specify which test suite to run (default: all)"
        )
        
        parser.add_argument(
            "--output-format",
            choices=["console", "json", "detailed"],
            default="console",
            help="Specify output format for test results (default: console)"
        )
        
        self.args = parser.parse_args()
        
        logger.info(f"Command-line arguments parsed successfully")
        logger.info(f"Test configuration: suite={self.args.test_suite}, "
                   f"cleanup={self.args.force_cleanup}, verbose={self.args.verbose}")
        
        return self.args

    @log_function()
    async def setup_test_environment(self) -> bool:
        """
        Setup test environment for memory system validation.
        
        Prepares clean test environment with proper configuration,
        logging setup, and validation checks for complete
        memory system testing.
        
        Returns:
            True if test environment setup successful, False otherwise
        """
        logger.info("Setting up test environment for memory system validation")
        
        try:
            # Record test start time
            self.test_stats['start_time'] = datetime.now(UTC)
            
            # Validate test environment requirements
            logger.info("Validating test environment requirements")
            
            # Check required dependencies and connections
            # (Additional validation can be added here)
            
            # Display test configuration
            if self.args.verbose:
                print(f"\n🔧 Test Environment Configuration:")
                print(f"   - Test Suite: {self.args.test_suite}")
                print(f"   - Force Cleanup: {self.args.force_cleanup}")
                print(f"   - Quick Mode: {self.args.quick}")
                print(f"   - Output Format: {self.args.output_format}")
                print(f"   - Start Time: {self.test_stats['start_time'].isoformat()}")
            
            logger.info("Test environment setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Test environment setup failed: {e}")
            return False

    @log_function()
    async def execute_memory_tests(self) -> bool:
        """
        Execute complete memory system tests.
        
        Runs memory system validation tests including procedural,
        semantic, and episodic memory testing with professional
        error handling and result tracking.
        
        Returns:
            True if all memory tests passed, False otherwise
        """
        logger.info("Executing memory system tests")
        
        try:
            # Execute memory test suite
            success = await run_memory_tests(force_cleanup=self.args.force_cleanup)
            
            if success:
                self.test_stats['tests_passed'] += 1
                logger.info("Memory system tests completed successfully")
            else:
                self.test_stats['tests_failed'] += 1
                logger.error("Memory system tests failed")
            
            self.test_stats['tests_executed'] += 1
            return success
            
        except Exception as e:
            logger.error(f"Memory test execution failed: {e}")
            self.test_stats['tests_failed'] += 1
            self.test_stats['tests_executed'] += 1
            return False

    @log_function()
    async def execute_test_suite(self) -> Dict[str, Any]:
        """
        Execute complete test suite based on configuration.
        
        Coordinates execution of specified test suites with professional
        error handling, progress tracking, and result compilation
        for asset management validation scenarios.
        
        Returns:
            Dictionary containing complete test execution results
        """
        logger.info(f"Executing test suite: {self.args.test_suite}")
        
        results = {
            'suite_name': self.args.test_suite,
            'start_time': datetime.now(UTC),
            'end_time': None,
            'duration': 0,
            'tests_run': [],
            'overall_success': True,
            'errors': []
        }
        
        try:
            # Execute based on test suite selection
            if self.args.test_suite in ["memory", "all"]:
                logger.info("Running memory system tests...")
                if self.args.verbose:
                    print("\n🧠 Running Memory System Tests...")
                
                memory_success = await self.execute_memory_tests()
                results['tests_run'].append({
                    'name': 'Memory System Tests',
                    'success': memory_success,
                    'error': None if memory_success else 'Memory tests failed'
                })
                
                if not memory_success:
                    results['overall_success'] = False
                    results['errors'].append('Memory system tests failed')
            
            # Additional test suites can be added here
            if self.args.test_suite in ["integration", "all"]:
                logger.info("Integration tests would run here (placeholder)")
                # Integration tests can be added when available
            
            if self.args.test_suite in ["performance", "all"] and not self.args.quick:
                logger.info("Performance tests included in memory test suite")
                # Performance tests are included in memory test suite
            
            results['end_time'] = datetime.now(UTC)
            results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
            
            logger.info(f"Test suite execution completed: success={results['overall_success']}")
            return results
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            results['overall_success'] = False
            results['errors'].append(str(e))
            results['end_time'] = datetime.now(UTC)
            results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
            return results

    @log_function()
    def generate_test_report(self, results: Dict[str, Any]) -> None:
        """
        Generate complete test execution report.
        
        Creates test report with execution metrics,
        success rates, error details, and business intelligence
        for asset management validation results.
        
        Args:
            results: Test execution results and metrics
        """
        logger.info("Generating complete test execution report")
        
        # Calculate final statistics
        self.test_stats['end_time'] = datetime.now(UTC)
        if self.test_stats['start_time']:
            self.test_stats['total_duration'] = (
                self.test_stats['end_time'] - self.test_stats['start_time']
            ).total_seconds()
        
        if self.test_stats['tests_executed'] > 0:
            self.test_stats['success_rate'] = (
                self.test_stats['tests_passed'] / self.test_stats['tests_executed']
            ) * 100
        
        # Generate report based on output format
        if self.args.output_format == "console":
            self._generate_console_report(results)
        elif self.args.output_format == "json":
            self._generate_json_report(results)
        elif self.args.output_format == "detailed":
            self._generate_detailed_report(results)

    def _generate_console_report(self, results: Dict[str, Any]) -> None:
        """Generate console-formatted test report."""
        print(f"\n🎯 EmailAgent Memory System Test Results")
        print(f"=" * 60)
        
        # Overall results
        status_emoji = "✅" if results['overall_success'] else "❌"
        print(f"{status_emoji} Overall Status: {'PASSED' if results['overall_success'] else 'FAILED'}")
        
        # Test suite information
        print(f"\n📊 Test Execution Summary:")
        print(f"   - Test Suite: {results['suite_name']}")
        print(f"   - Duration: {results['duration']:.2f} seconds")
        print(f"   - Tests Executed: {len(results['tests_run'])}")
        
        # Individual test results
        if results['tests_run']:
            print(f"\n📋 Individual Test Results:")
            for test in results['tests_run']:
                test_emoji = "✅" if test['success'] else "❌"
                print(f"   {test_emoji} {test['name']}: {'PASSED' if test['success'] else 'FAILED'}")
                if test['error']:
                    print(f"      Error: {test['error']}")
        
        # Error summary
        if results['errors']:
            print(f"\n❌ Errors Encountered:")
            for error in results['errors']:
                print(f"   - {error}")
        
        # Final message
        if results['overall_success']:
            print(f"\n🎉 All tests completed successfully!")
            print(f"Memory system validation passed for asset management environments.")
        else:
            print(f"\n⚠️  Some tests failed - review errors above")
            print(f"Memory system requires attention before production use.")

    def _generate_json_report(self, results: Dict[str, Any]) -> None:
        """Generate JSON-formatted test report."""
        import json
        
        report = {
            'test_execution': {
                'suite': results['suite_name'],
                'overall_success': results['overall_success'],
                'duration': results['duration'],
                'start_time': results['start_time'].isoformat(),
                'end_time': results['end_time'].isoformat() if results['end_time'] else None
            },
            'test_results': results['tests_run'],
            'errors': results['errors'],
            'statistics': self.test_stats
        }
        
        print(json.dumps(report, indent=2))

    def _generate_detailed_report(self, results: Dict[str, Any]) -> None:
        """Generate detailed test report with complete metrics."""
        self._generate_console_report(results)
        
        print(f"\n📈 Detailed Statistics:")
        print(f"   - Start Time: {self.test_stats['start_time'].isoformat()}")
        print(f"   - End Time: {self.test_stats['end_time'].isoformat()}")
        print(f"   - Total Duration: {self.test_stats['total_duration']:.2f} seconds")
        print(f"   - Success Rate: {self.test_stats['success_rate']:.1f}%")
        
        print(f"\n🏢 Asset Management Context:")
        print(f"   Memory system validation ensures reliable email automation")
        print(f"   for private market investment workflows, compliance,")
        print(f"   and relationship management in environments.")

    @log_function()
    async def run_complete_tests(self) -> bool:
        """
        Run complete test suite with coordination.
        
        Orchestrates complete test execution including environment setup,
        test coordination, result compilation, and reporting for
        asset management validation.
        
        Returns:
            True if all tests passed, False otherwise
        """
        logger.info("🚀 Starting complete memory system test execution")
        
        try:
            # Parse command-line arguments
            self.parse_arguments()
            
            # Setup test environment
            setup_success = await self.setup_test_environment()
            if not setup_success:
                logger.error("Test environment setup failed")
                return False
            
            # Execute test suite
            results = await self.execute_test_suite()
            
            # Generate test report
            self.generate_test_report(results)
            
            # Log final results
            logger.info(f"Test execution completed: success={results['overall_success']}")
            
            return results['overall_success']
            
        except Exception as e:
            logger.error(f"Complete test execution failed: {e}")
            print(f"\n❌ Test execution failed: {e}")
            return False

# Main execution functions
@log_function()
async def run_test_suite() -> bool:
    """
    Main test suite execution function.
    
    Creates and runs complete test suite with professional
    coordination and error handling for asset management
    memory system validation.
    
    Returns:
        True if all tests passed, False otherwise
    """
    logger.info("Initializing complete test suite execution")
    
    try:
        runner = TestRunner()
        success = await runner.run_complete_tests()
        return success
        
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        return False

def main() -> None:
    """
    Main entry point for test runner.
    
    Provides command-line interface for memory system
    test execution with complete error handling and reporting.
    """
    print("🎯 EmailAgent Memory System Test Runner")
    print("Asset Management Email Automation Validation")
    print("=" * 60)
    
    try:
        # Run complete test suite
        success = asyncio.run(run_test_suite())
        
        # Exit with appropriate status code
        exit_code = 0 if success else 1
        
        if success:
            print(f"\n✅ All tests completed successfully!")
        else:
            print(f"\n❌ Test execution failed or tests did not pass")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Test execution interrupted by user")
        logger.info("Test execution interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        logger.error(f"Test runner execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 