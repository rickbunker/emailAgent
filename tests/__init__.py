"""
Main Test Package for EmailAgent

Comprehensive testing infrastructure for private market asset management email automation.
Provides professional test suites, integration testing, performance validation,
and quality assurance for production EmailAgent deployments.

Features:
    - Multi-tier testing framework (unit, integration, performance)
    - Email system integration testing with Gmail and Microsoft Graph
    - Memory system testing and validation
    - Performance benchmarking and load testing
    - Security testing and vulnerability assessment
    - Business workflow testing for asset management scenarios

Business Context:
    Designed for asset management firms requiring enterprise-grade
    testing and validation of email automation systems with comprehensive
    quality assurance, regulatory compliance testing, and performance
    validation for mission-critical production environments.

Technical Architecture:
    - Unit Tests: Individual component testing and validation
    - Integration Tests: Cross-system workflow and interaction testing
    - Performance Tests: Load testing, benchmarking, and scalability
    - Security Tests: Security scanning, penetration testing, validation
    - Business Tests: Asset management workflow and compliance testing

Test Organization:
    - Email Integration: Gmail, Microsoft Graph authentication and processing
    - Memory Systems: Memory component testing and data persistence
    - Logging Systems: Logging infrastructure and integration testing
    - Performance: Load testing, benchmarking, and optimization validation
    - Security: Authentication, authorization, and security validation

Version: 1.0.0
Author: Email Agent Development Team
License: Private - Asset Management Use Only
"""

import os
import sys
from typing import Dict, List, Optional, Any

# Test framework imports
try:
    import unittest
    import pytest
    import asyncio
    from datetime import datetime, UTC
except ImportError as e:
    print(f"Warning: Missing test framework dependency: {e}")

# Package metadata
__version__ = "1.0.0"
__author__ = "Email Agent Development Team"
__license__ = "Private - Asset Management Use Only"

# Test categories and organization
TEST_CATEGORIES = {
    'unit': {
        'description': 'Unit tests for individual components',
        'test_files': [
            'test_logging_system.py'
        ],
        'estimated_duration': 120,  # seconds
        'priority': 'high'
    },
    'integration': {
        'description': 'Integration tests for system workflows',
        'test_files': [
            'test_gmail_integration.py',
            'test_msgraph_integration.py',
            'test_logging_integration.py'
        ],
        'estimated_duration': 300,
        'priority': 'high'
    },
    'performance': {
        'description': 'Performance and load testing',
        'test_files': [
            'test_100_real_emails.py',
            'test_emails_with_attachments.py',
            'test_phase3_classification.py'
        ],
        'estimated_duration': 600,
        'priority': 'medium'
    },
    'security': {
        'description': 'Security and authentication testing',
        'test_files': [
            'test_msgraph_web_auth.py',
            'test_msgraph_connection.py'
        ],
        'estimated_duration': 180,
        'priority': 'high'
    },
    'demo': {
        'description': 'Demonstration and example workflows',
        'test_files': [
            'simple_phase3_test.py'
        ],
        'estimated_duration': 90,
        'priority': 'low'
    }
}

# Public API exports
__all__ = [
    '__version__',
    '__author__',
    '__license__',
    'TEST_CATEGORIES',
    'get_test_categories',
    'get_test_files',
    'validate_test_environment'
]

def get_test_categories() -> List[str]:
    """
    Get list of available test categories.
    
    Returns:
        List of test category names
    """
    return list(TEST_CATEGORIES.keys())

def get_test_files(category: Optional[str] = None) -> List[str]:
    """
    Get list of test files for a specific category or all categories.
    
    Args:
        category: Optional category filter
        
    Returns:
        List of test file names
    """
    if category:
        if category not in TEST_CATEGORIES:
            raise ValueError(f"Unknown test category: {category}")
        return TEST_CATEGORIES[category]['test_files']
    
    # Return all test files
    all_files = []
    for cat_info in TEST_CATEGORIES.values():
        all_files.extend(cat_info['test_files'])
    return all_files

def validate_test_environment() -> Dict[str, Any]:
    """
    Validate test environment readiness and configuration.
    
    Returns:
        Dictionary containing validation results and recommendations
    """
    validation_results = {
        'ready': True,
        'timestamp': datetime.now(UTC).isoformat() if 'UTC' in globals() else 'unknown',
        'test_framework_available': False,
        'dependencies': {},
        'recommendations': [],
        'warnings': []
    }
    
    try:
        # Check test framework availability
        try:
            import unittest
            import pytest
            validation_results['test_framework_available'] = True
            validation_results['dependencies']['unittest'] = True
            validation_results['dependencies']['pytest'] = True
        except ImportError:
            validation_results['test_framework_available'] = False
            validation_results['warnings'].append('Test framework dependencies missing')
            validation_results['recommendations'].append('Install pytest and unittest')
        
        # Check asyncio support
        try:
            import asyncio
            validation_results['dependencies']['asyncio'] = True
        except ImportError:
            validation_results['dependencies']['asyncio'] = False
            validation_results['warnings'].append('Asyncio support missing')
        
        # Overall readiness
        validation_results['ready'] = validation_results['test_framework_available']
        
        return validation_results
        
    except Exception as e:
        validation_results['ready'] = False
        validation_results['error'] = str(e)
        validation_results['recommendations'].append('Check system configuration and dependencies')
        return validation_results 