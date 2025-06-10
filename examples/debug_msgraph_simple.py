#!/usr/bin/env python3
"""
Simple debug script to show Microsoft Graph request parameters.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria

def build_filter_debug(criteria):
    """Debug version of the filter building logic."""
    filters = []
    
    print("🔧 Building filters from criteria:")
    print(f"   has_attachments: {criteria.has_attachments}")
    print(f"   max_results: {criteria.max_results}")
    print(f"   date_after: {criteria.date_after}")
    print(f"   date_before: {criteria.date_before}")
    
    # Copy the exact logic from msgraph.py
    if criteria.has_attachments:
        filter_part = "hasAttachments eq true"
        filters.append(filter_part)
        print(f"   Added filter: {filter_part}")
    
    if criteria.date_after:
        iso_date = criteria.date_after.strftime('%Y-%m-%dT%H:%M:%SZ')
        filter_part = f"receivedDateTime ge '{iso_date}'"
        filters.append(filter_part)
        print(f"   Added filter: {filter_part}")
    
    if criteria.date_before:
        iso_date = criteria.date_before.strftime('%Y-%m-%dT%H:%M:%SZ')
        filter_part = f"receivedDateTime le '{iso_date}'"
        filters.append(filter_part)
        print(f"   Added filter: {filter_part}")
    
    # Build params like the real code
    params = {
        '$top': str(criteria.max_results),
        '$orderby': 'receivedDateTime desc'
    }
    
    if filters:
        params['$filter'] = ' and '.join(filters)
    
    print(f"🌐 Final URL parameters:")
    for key, value in params.items():
        print(f"   {key}: {value}")
    
    return params

async def debug_simple():
    """Simple debug of Microsoft Graph parameters."""
    print("🔍 Microsoft Graph Parameter Debug")
    
    # Test 1: Working case (no filters)
    print("\n📧 Test 1: No filters (should work)")
    criteria1 = EmailSearchCriteria(max_results=5)
    params1 = build_filter_debug(criteria1)
    
    # Test 2: With attachments (currently failing)
    print("\n📧 Test 2: With attachments filter (currently failing)")
    criteria2 = EmailSearchCriteria(has_attachments=True, max_results=5)
    params2 = build_filter_debug(criteria2)
    
    # Test 3: Manual construction of working params
    print("\n📧 Test 3: Manual construction that should work")
    manual_params = {
        '$filter': 'hasAttachments eq true',
        '$top': '5'
    }
    print(f"🌐 Manual parameters:")
    for key, value in manual_params.items():
        print(f"   {key}: {value}")
    
    print("\n🎯 The issue might be in parameter encoding or the '$orderby' parameter!")

if __name__ == "__main__":
    asyncio.run(debug_simple()) 