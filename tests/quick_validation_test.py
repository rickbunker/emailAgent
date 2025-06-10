#!/usr/bin/env python3
"""
Quick validation test for EmailAgent improvements.

Tests basic functionality after adding type hints, logging, and docstrings.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from memory.contact import ContactMemory, ContactType, ContactConfidence
from utils.logging_system import get_logger, log_function, LogConfig, configure_logging

# Configure logging for test
test_config = LogConfig(
    level="INFO",
    log_to_file=False,  # Only console for this quick test
    log_to_stdout=True,
    log_arguments=False,
    log_return_values=False,
    log_execution_time=True
)
configure_logging(test_config)

logger = get_logger(__name__)

@log_function()
async def test_memory_system() -> bool:
    """Test basic memory system functionality."""
    logger.info("Testing memory system with new improvements")
    
    try:
        # Test contact memory
        memory = ContactMemory(max_items=10)
        
        contact_id = await memory.add_contact(
            email='test@example.com',
            name='Test User',
            organization='Test Company',
            contact_type=ContactType.PROFESSIONAL,
            confidence=ContactConfidence.HIGH
        )
        
        # Retrieve contact
        contact = await memory.find_contact_by_email('test@example.com')
        
        if contact and contact.name == 'Test User':
            logger.info("✅ Contact memory test passed!")
            return True
        else:
            logger.error("❌ Contact memory test failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Memory test error: {e}")
        return False

@log_function()
def test_logging_system() -> bool:
    """Test logging system functionality."""
    logger.info("Testing logging system improvements")
    
    try:
        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        
        # Test function decoration
        @log_function()
        def sample_function(x: int, y: str = "default") -> dict:
            return {"result": x, "message": y}
        
        result = sample_function(42, "test")
        
        if result and result["result"] == 42:
            logger.info("✅ Logging system test passed!")
            return True
        else:
            logger.error("❌ Logging system test failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Logging test error: {e}")
        return False

async def main() -> None:
    """Run quick validation tests."""
    print("🧪 Quick Validation Test for EmailAgent Improvements")
    print("=" * 60)
    
    # Test logging system
    logging_result = test_logging_system()
    
    # Test memory system  
    memory_result = await test_memory_system()
    
    # Summary
    print("\n📊 Test Results:")
    print(f"   Logging System: {'✅ PASS' if logging_result else '❌ FAIL'}")
    print(f"   Memory System:  {'✅ PASS' if memory_result else '❌ FAIL'}")
    
    overall_success = logging_result and memory_result
    print(f"\n🎯 Overall Result: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")
    
    if overall_success:
        print("\n🎉 All improvements are working correctly!")
    else:
        print("\n⚠️  Some issues detected - check logs above")

if __name__ == "__main__":
    asyncio.run(main()) 