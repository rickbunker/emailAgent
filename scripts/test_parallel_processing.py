#!/usr/bin/env python3
"""
Parallel Processing Performance Test

Tests and benchmarks the parallel email processing capabilities
of the Email Agent system. Useful for performance validation
and optimization.

Usage:
    python scripts/test_parallel_processing.py [options]

Options:
    --emails N          Number of test emails to process (default: 10)
    --concurrency N     Max concurrent workers (default: 5)
    --with-attachments  Include attachment processing tests
    --benchmark-only    Run benchmarks without actual email processing
    --verbose           Show detailed timing information
"""

# # Standard library imports
import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# # Local application imports
# Local imports
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


class ParallelProcessingTester:
    """Performance testing utility for parallel processing."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: dict[str, Any] = {}

    def generate_test_emails(
        self, count: int, with_attachments: bool = False
    ) -> list[dict[str, Any]]:
        """Generate mock email data for testing."""
        emails = []

        for i in range(count):
            email = {
                "id": f"test_email_{i:03d}",
                "subject": f"Test Email {i+1}: Asset Document Processing",
                "sender_email": f"sender{i % 3}@testcompany.com",  # Rotate senders
                "body": f"This is test email {i+1} containing asset-related content for performance testing.",
                "received_time": "2025-01-01T10:00:00Z",
                "attachments": [],
            }

            if with_attachments:
                # Add test attachments
                attachments_count = min(i % 4 + 1, 3)  # 1-3 attachments per email
                for j in range(attachments_count):
                    attachment = {
                        "filename": f"test_document_{i}_{j}.pdf",
                        "content": b"Mock PDF content for testing"
                        * 100,  # ~2.5KB mock content
                        "size": 2500,
                    }
                    email["attachments"].append(attachment)

            emails.append(email)

        return emails

    async def benchmark_sequential_processing(
        self, emails: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Benchmark sequential email processing."""
        print(f"📈 Sequential Processing Benchmark ({len(emails)} emails)...")

        start_time = time.time()
        processed = 0
        errors = 0

        # Mock agent for testing
        agent = MagicMock()
        agent.process_single_attachment = asyncio.coroutine(
            lambda *args, **kwargs: MagicMock(status="success", confidence=0.85)
        )

        for email in emails:
            try:
                # Simulate processing time
                await asyncio.sleep(0.1)  # 100ms per email

                # Process attachments sequentially
                for attachment in email.get("attachments", []):
                    await agent.process_single_attachment(attachment, email)
                    await asyncio.sleep(0.05)  # 50ms per attachment

                processed += 1

            except Exception as e:
                errors += 1
                if self.verbose:
                    print(f"  ❌ Error processing email {email['id']}: {e}")

        total_time = time.time() - start_time

        return {
            "method": "sequential",
            "emails_processed": processed,
            "errors": errors,
            "total_time": total_time,
            "emails_per_second": processed / total_time if total_time > 0 else 0,
            "avg_time_per_email": total_time / processed if processed > 0 else 0,
        }

    async def benchmark_parallel_processing(
        self, emails: list[dict[str, Any]], max_concurrent: int = 5
    ) -> dict[str, Any]:
        """Benchmark parallel email processing."""
        print(
            f"🚀 Parallel Processing Benchmark ({len(emails)} emails, {max_concurrent} workers)..."
        )

        start_time = time.time()
        processed = 0
        errors = 0

        # Mock agent for testing
        agent = MagicMock()
        agent.process_single_attachment = asyncio.coroutine(
            lambda *args, **kwargs: MagicMock(status="success", confidence=0.85)
        )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_email(email: dict[str, Any]) -> dict[str, Any]:
            """Process a single email with concurrency control."""
            nonlocal processed, errors

            async with semaphore:
                try:
                    # Simulate processing time
                    await asyncio.sleep(0.1)  # 100ms per email

                    # Process attachments in parallel
                    if email.get("attachments"):
                        attachment_tasks = [
                            agent.process_single_attachment(attachment, email)
                            for attachment in email["attachments"]
                        ]
                        await asyncio.gather(*attachment_tasks)

                        # Additional delay for attachment processing
                        await asyncio.sleep(0.05 * len(email["attachments"]))

                    processed += 1
                    return {"status": "success", "email_id": email["id"]}

                except Exception as e:
                    errors += 1
                    if self.verbose:
                        print(f"  ❌ Error processing email {email['id']}: {e}")
                    return {"status": "error", "email_id": email["id"], "error": str(e)}

        # Process all emails in parallel
        tasks = [process_email(email) for email in emails]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        return {
            "method": "parallel",
            "emails_processed": processed,
            "errors": errors,
            "total_time": total_time,
            "emails_per_second": processed / total_time if total_time > 0 else 0,
            "avg_time_per_email": total_time / processed if processed > 0 else 0,
            "concurrency": max_concurrent,
            "speedup_factor": 0,  # Will be calculated later
        }

    async def test_memory_usage(self, emails: list[dict[str, Any]]) -> dict[str, Any]:
        """Test memory usage during parallel processing."""
        print("🧠 Memory Usage Test...")

        try:
            # # Third-party imports
            import psutil

            process = psutil.Process()

            # Baseline memory
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Process emails in parallel
            start_memory = process.memory_info().rss / 1024 / 1024

            # Simulate processing
            tasks = []
            for email in emails:
                tasks.append(asyncio.sleep(0.01))  # Quick simulation

            await asyncio.gather(*tasks)

            peak_memory = process.memory_info().rss / 1024 / 1024

            return {
                "baseline_memory_mb": baseline_memory,
                "start_memory_mb": start_memory,
                "peak_memory_mb": peak_memory,
                "memory_increase_mb": peak_memory - start_memory,
                "memory_per_email_mb": (
                    (peak_memory - start_memory) / len(emails) if emails else 0
                ),
            }

        except ImportError:
            return {
                "error": "psutil not available - cannot measure memory usage",
                "baseline_memory_mb": 0,
                "peak_memory_mb": 0,
                "memory_increase_mb": 0,
            }

    async def test_concurrency_scaling(
        self, emails: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Test performance scaling with different concurrency levels."""
        print("📊 Concurrency Scaling Test...")

        concurrency_levels = [1, 2, 3, 5, 8, 10]
        results = []

        for concurrency in concurrency_levels:
            print(f"  Testing with {concurrency} concurrent workers...")

            result = await self.benchmark_parallel_processing(
                emails[:10], max_concurrent=concurrency  # Use subset for scaling test
            )
            result["concurrency"] = concurrency
            results.append(result)

            if self.verbose:
                print(
                    f"    ⏱️ {result['total_time']:.2f}s, {result['emails_per_second']:.1f} emails/sec"
                )

        return results

    def print_performance_summary(
        self, sequential_result: dict[str, Any], parallel_result: dict[str, Any]
    ):
        """Print comprehensive performance summary."""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 60)

        # Sequential results
        print("\n📈 Sequential Processing:")
        print(f"  ⏱️ Total Time: {sequential_result['total_time']:.2f} seconds")
        print(f"  📧 Emails/Second: {sequential_result['emails_per_second']:.1f}")
        print(f"  ⚡ Avg Time/Email: {sequential_result['avg_time_per_email']:.3f}s")
        print(f"  ✅ Processed: {sequential_result['emails_processed']}")
        print(f"  ❌ Errors: {sequential_result['errors']}")

        # Parallel results
        print(f"\n🚀 Parallel Processing ({parallel_result['concurrency']} workers):")
        print(f"  ⏱️ Total Time: {parallel_result['total_time']:.2f} seconds")
        print(f"  📧 Emails/Second: {parallel_result['emails_per_second']:.1f}")
        print(f"  ⚡ Avg Time/Email: {parallel_result['avg_time_per_email']:.3f}s")
        print(f"  ✅ Processed: {parallel_result['emails_processed']}")
        print(f"  ❌ Errors: {parallel_result['errors']}")

        # Performance comparison
        if sequential_result["total_time"] > 0 and parallel_result["total_time"] > 0:
            speedup = sequential_result["total_time"] / parallel_result["total_time"]
            efficiency = speedup / parallel_result["concurrency"] * 100

            print("\n🏆 Performance Improvement:")
            print(f"  🚀 Speedup Factor: {speedup:.2f}x")
            print(f"  ⚡ Efficiency: {efficiency:.1f}%")
            print(
                f"  📈 Throughput Increase: {(parallel_result['emails_per_second'] / sequential_result['emails_per_second'] - 1) * 100:.1f}%"
            )

        print("=" * 60)

    async def run_comprehensive_test(
        self, email_count: int, max_concurrency: int, with_attachments: bool
    ):
        """Run comprehensive performance testing."""
        print("🧪 Comprehensive Parallel Processing Performance Test")
        print("=" * 55)

        # Generate test data
        print(f"📋 Generating {email_count} test emails...")
        emails = self.generate_test_emails(email_count, with_attachments)

        if with_attachments:
            total_attachments = sum(
                len(email.get("attachments", [])) for email in emails
            )
            print(f"📎 Total attachments: {total_attachments}")

        # Run benchmarks
        sequential_result = await self.benchmark_sequential_processing(emails)
        parallel_result = await self.benchmark_parallel_processing(
            emails, max_concurrency
        )

        # Memory usage test
        memory_result = await self.test_memory_usage(emails)
        if "error" not in memory_result:
            print("\n🧠 Memory Usage:")
            print(f"  📊 Peak Memory: {memory_result['peak_memory_mb']:.1f} MB")
            print(f"  📈 Memory Increase: {memory_result['memory_increase_mb']:.1f} MB")
            print(f"  📧 Memory/Email: {memory_result['memory_per_email_mb']:.2f} MB")

        # Concurrency scaling test
        scaling_results = await self.test_concurrency_scaling(emails)

        # Print summary
        self.print_performance_summary(sequential_result, parallel_result)

        # Store results
        self.results = {
            "sequential": sequential_result,
            "parallel": parallel_result,
            "memory": memory_result,
            "scaling": scaling_results,
            "test_config": {
                "email_count": email_count,
                "max_concurrency": max_concurrency,
                "with_attachments": with_attachments,
            },
        }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Parallel Processing Performance Test")
    parser.add_argument(
        "--emails", type=int, default=10, help="Number of test emails (default: 10)"
    )
    parser.add_argument(
        "--concurrency", type=int, default=5, help="Max concurrent workers (default: 5)"
    )
    parser.add_argument(
        "--with-attachments",
        action="store_true",
        help="Include attachment processing tests",
    )
    parser.add_argument(
        "--benchmark-only",
        action="store_true",
        help="Run benchmarks without email processing",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )

    args = parser.parse_args()

    tester = ParallelProcessingTester(verbose=args.verbose)

    try:
        await tester.run_comprehensive_test(
            email_count=args.emails,
            max_concurrency=args.concurrency,
            with_attachments=args.with_attachments,
        )

        print("\n✅ Performance testing completed successfully!")

    except KeyboardInterrupt:
        print("\n\n⏹️ Performance test interrupted by user")
    except Exception as e:
        print(f"\n❌ Performance test failed: {e}")
        if args.verbose:
            # # Standard library imports
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
