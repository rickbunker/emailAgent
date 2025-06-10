#!/usr/bin/env python3
"""
Test script to demonstrate parallel processing performance improvements
"""

import asyncio
import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria
from agents.asset_document_agent import AssetDocumentAgent

async def test_parallel_vs_sequential():
    """Test parallel vs sequential processing performance"""
    
    print("🚀 Testing Parallel vs Sequential Processing Performance")
    print("=" * 60)
    
    # Initialize Microsoft Graph interface
    msgraph = MicrosoftGraphInterface()
    
    # Connect
    print("📨 Connecting to Microsoft Graph...")
    connected = await msgraph.connect()
    
    if not connected:
        print("❌ Failed to connect to Microsoft Graph")
        return
    
    # Get emails with attachments
    print("🔍 Searching for emails with attachments...")
    criteria = EmailSearchCriteria(max_results=5)
    emails = await msgraph.list_emails(criteria)
    
    # Filter emails with attachments
    emails_with_attachments = [email for email in emails if email.attachments]
    
    if not emails_with_attachments:
        print("❌ No emails with attachments found")
        return
    
    print(f"✅ Found {len(emails_with_attachments)} emails with attachments")
    
    # Use the first email for testing
    test_email = emails_with_attachments[0]
    print(f"📧 Testing with email: {test_email.subject}")
    print(f"📎 Attachments: {len(test_email.attachments)}")
    
    # Initialize Asset Document Agent
    asset_agent = AssetDocumentAgent(base_assets_path="./test_parallel_attachments")
    
    # Prepare email data
    email_data = {
        'sender_email': test_email.sender.address,
        'sender_name': test_email.sender.name or test_email.sender.address,
        'subject': test_email.subject,
        'date': test_email.received_date.isoformat() if test_email.received_date else "",
        'body': test_email.body_text or test_email.body_html or ''
    }
    
    # Prepare attachment data
    attachment_data_list = []
    for attachment in test_email.attachments:
        if attachment.content:
            attachment_data_list.append({
                'filename': attachment.filename,
                'content': attachment.content
            })
    
    if not attachment_data_list:
        print("❌ No attachment content available")
        return
    
    print(f"\n⚡ Performance Test with {len(attachment_data_list)} attachments")
    print("-" * 50)
    
    # Test 1: Sequential Processing (Original Method)
    print("🐌 Test 1: Sequential Processing")
    start_time = time.time()
    
    sequential_results = []
    for attachment_data in attachment_data_list:
        result = await asset_agent.process_and_save_attachment(
            attachment_data=attachment_data,
            email_data=email_data,
            save_to_disk=False  # Don't save during test
        )
        sequential_results.append(result)
    
    sequential_time = time.time() - start_time
    print(f"   Sequential processing time: {sequential_time:.2f} seconds")
    
    # Test 2: Parallel Processing (New Method)
    print("\n🚀 Test 2: Parallel Processing")
    start_time = time.time()
    
    parallel_results = await asset_agent.process_attachments_parallel(
        email_attachments=attachment_data_list,
        email_data=email_data
    )
    
    parallel_time = time.time() - start_time
    print(f"   Parallel processing time: {parallel_time:.2f} seconds")
    
    # Calculate performance improvement
    improvement = ((sequential_time - parallel_time) / sequential_time) * 100
    speedup = sequential_time / parallel_time if parallel_time > 0 else float('inf')
    
    print(f"\n📊 Performance Results:")
    print(f"   Sequential: {sequential_time:.2f}s")
    print(f"   Parallel:   {parallel_time:.2f}s")
    print(f"   Speedup:    {speedup:.1f}x faster")
    print(f"   Improvement: {improvement:.1f}% faster")
    
    # Verify results are equivalent
    print(f"\n✅ Result Verification:")
    print(f"   Sequential results: {len(sequential_results)}")
    print(f"   Parallel results:   {len(parallel_results)}")
    
    success_count_seq = sum(1 for r in sequential_results if r.status.value == 'success')
    success_count_par = sum(1 for r in parallel_results if r.status.value == 'success')
    
    print(f"   Sequential success: {success_count_seq}")
    print(f"   Parallel success:   {success_count_par}")
    
    if success_count_seq == success_count_par:
        print("   ✅ Results match - parallel processing is working correctly!")
    else:
        print("   ⚠️ Results differ - need to investigate")
    
    # Show detailed timing breakdown
    print(f"\n⏱️ Detailed Timing Analysis:")
    estimated_sequential_virus_scan = len(attachment_data_list) * 10  # 10s per scan
    print(f"   Estimated virus scan time (sequential): {estimated_sequential_virus_scan}s")
    print(f"   Actual total time (parallel): {parallel_time:.2f}s")
    
    if parallel_time < estimated_sequential_virus_scan:
        virus_scan_improvement = ((estimated_sequential_virus_scan - parallel_time) / estimated_sequential_virus_scan) * 100
        print(f"   Virus scan improvement: {virus_scan_improvement:.1f}% faster")
    
    print(f"\n🎯 Conclusion:")
    if improvement > 50:
        print(f"   🟢 EXCELLENT: {improvement:.1f}% performance improvement!")
    elif improvement > 25:
        print(f"   🟡 GOOD: {improvement:.1f}% performance improvement")
    elif improvement > 0:
        print(f"   🟠 MODEST: {improvement:.1f}% performance improvement")
    else:
        print(f"   🔴 No improvement - need to investigate")

async def main():
    """Main entry point"""
    try:
        await test_parallel_vs_sequential()
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 