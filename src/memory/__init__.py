"""
Memory Systems Package for EmailAgent

Complete memory management package for private market asset management environments.
Provides memory architectures including episodic, semantic, procedural,
and contact memory systems with vector-based storage and retrieval.

Features:
    - Multi-modal memory architecture for different knowledge types
    - Vector-based storage with Qdrant integration
    - Semantic search and contextual retrieval
    - business context and intelligence
    - Memory lifecycle management and optimization
    - performance and scalability

Business Context:
    Designed for asset management firms requiring memory systems
    for relationship management, knowledge retention, process automation,
    and business intelligence. Maintains institutional memory across deal flow,
    investor relations, operational procedures, and decision support.

Technical Architecture:
    - BaseMemory: Abstract foundation for all memory systems
    - EpisodicMemory: Conversation history and temporal event tracking
    - SemanticMemory: Knowledge storage and relationship intelligence
    - ProceduralMemory: Business rules and workflow automation
    - ContactMemory: Contact management and relationship tracking

Memory Types:
    - Base: Abstract memory interface with vector storage
    - Episodic: Temporal memories and conversation history
    - Semantic: Knowledge and relationship intelligence
    - Procedural: Business rules and automation procedures
    - Contact: Contact records and relationship management

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# Core logging system
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_system import get_logger, log_function

# Initialize package logger
logger = get_logger(__name__)

# Core memory interfaces and base classes
from .base import BaseMemory, MemoryItem

# Specialized memory system implementations
from .episodic import EpisodicMemory, EpisodicMemoryType
from .semantic import SemanticMemory, KnowledgeType, KnowledgeConfidence
from .procedural import ProceduralMemory, RuleType, RulePriority, RuleConfidence
from .contact import ContactMemory, ContactRecord, ContactType, ContactConfidence

# Package metadata
__version__ = "1.0.0"
__author__ = "Email Agent Development Team"
__license__ = "for Inveniam use only"

# Public API exports
__all__ = [
    # Core memory infrastructure
    'BaseMemory',
    'MemoryItem',
    
    # Episodic memory system
    'EpisodicMemory',
    'EpisodicMemoryType',
    
    # Semantic memory system
    'SemanticMemory',
    'KnowledgeType',
    'KnowledgeConfidence',
    
    # Procedural memory system
    'ProceduralMemory',
    'RuleType',
    'RulePriority',
    'RuleConfidence',
    
    # Contact memory system
    'ContactMemory',
    'ContactRecord',
    'ContactType',
    'ContactConfidence',
    
    # Package metadata
    '__version__',
    '__author__',
    '__license__'
]

# Package initialization logging
logger.info(f"Memory systems package initialized - Version {__version__}")
logger.debug(f"Available memory systems: Episodic, Semantic, Procedural, Contact")
logger.debug(f"Base memory infrastructure loaded with vector storage support")

# Package-level convenience functions
@log_function()
def create_memory_system(memory_type: str, **kwargs) -> BaseMemory:
    """
    Convenience function to create memory system instances.
    
    Provides package-level access to memory system instantiation
    with simplified parameter handling and type validation.
    
    Args:
        memory_type: Type of memory system ('episodic', 'semantic', 'procedural', 'contact')
        **kwargs: Memory system configuration parameters
        
    Returns:
        Configured memory system instance
        
    Raises:
        ValueError: If memory type unsupported or invalid
        
    Example:
        >>> from memory import create_memory_system
        >>> episodic = create_memory_system('episodic', max_items=2000)
        >>> contact = create_memory_system('contact', max_items=5000)
    """
    memory_type = memory_type.lower().strip()
    logger.info(f"Creating memory system via convenience function: {memory_type}")
    
    if memory_type == 'episodic':
        return EpisodicMemory(**kwargs)
    elif memory_type == 'semantic':
        return SemanticMemory(**kwargs)
    elif memory_type == 'procedural':
        return ProceduralMemory(**kwargs)
    elif memory_type == 'contact':
        return ContactMemory(**kwargs)
    else:
        supported_types = ['episodic', 'semantic', 'procedural', 'contact']
        raise ValueError(f"Unsupported memory type: '{memory_type}'. Supported types: {supported_types}")

@log_function()
def get_supported_memory_types() -> list:
    """
    Get list of supported memory system types.
    
    Returns:
        List of supported memory system type strings
        
    Example:
        >>> from memory import get_supported_memory_types
        >>> types = get_supported_memory_types()
        >>> print(types)
        ['episodic', 'semantic', 'procedural', 'contact']
    """
    return ['episodic', 'semantic', 'procedural', 'contact']

@log_function()
def get_memory_system_info(memory_type: str) -> dict:
    """
    Get complete information about a specific memory system type.
    
    Provides detailed information about memory system capabilities,
    use cases, and configuration options for deployment planning.
    
    Args:
        memory_type: Memory system type identifier
        
    Returns:
        Dictionary containing memory system information and capabilities
        
    Raises:
        ValueError: If memory type unsupported
        
    Example:
        >>> from memory import get_memory_system_info
        >>> info = get_memory_system_info('contact')
        >>> print(info['description'])
        'Contact management and relationship tracking memory system'
    """
    memory_type = memory_type.lower().strip()
    logger.info(f"Retrieving memory system information for: {memory_type}")
    
    system_info = {
        'episodic': {
            'name': 'Episodic Memory System',
            'description': 'Conversation history and temporal event tracking memory system',
            'capabilities': [
                'Conversation history storage and retrieval',
                'Temporal context management',
                'Event tracking and categorization',
                'Time-based search and filtering',
                'Participant tracking and analysis',
                'Business intelligence and insights'
            ],
            'use_cases': [
                'Email conversation tracking',
                'Investment meeting records',
                'Decision audit trails',
                'Client interaction history',
                'Compliance event tracking'
            ],
            'data_types': ['conversation', 'meeting', 'decision', 'feedback', 'event']
        },
        'semantic': {
            'name': 'Semantic Memory System',
            'description': 'Knowledge storage and relationship intelligence memory system',
            'capabilities': [
                'Sender intelligence and knowledge',
                'Email type classification patterns',
                'Domain expertise storage',
                'Relationship intelligence',
                'Knowledge confidence scoring',
                'Semantic search and retrieval'
            ],
            'use_cases': [
                'Counterparty intelligence',
                'Communication pattern analysis',
                'Industry knowledge management',
                'Email classification training',
                'Relationship context enrichment'
            ],
            'data_types': ['sender', 'email_type', 'domain', 'process', 'rule', 'insight']
        },
        'procedural': {
            'name': 'Procedural Memory System',
            'description': 'Business rules and workflow automation memory system',
            'capabilities': [
                'Business rule storage and management',
                'Workflow procedure automation',
                'Decision criteria and approval workflows',
                'Compliance rule enforcement',
                'Rule priority and confidence management',
                'Process optimization and learning'
            ],
            'use_cases': [
                'Investment approval workflows',
                'Compliance procedure enforcement',
                'Email classification rules',
                'Operational standard procedures',
                'Decision automation criteria'
            ],
            'data_types': ['investment', 'compliance', 'operational', 'communication', 'approval', 'classification']
        },
        'contact': {
            'name': 'Contact Memory System',
            'description': 'Contact management and relationship tracking memory system',
            'capabilities': [
                'Contact deduplication and management',
                'Relationship intelligence and tracking',
                'Interaction frequency analysis',
                'Contact enrichment over time',
                'Business context categorization',
                'confidence scoring'
            ],
            'use_cases': [
                'Investor relationship management',
                'Counterparty contact tracking',
                'Business development contacts',
                'Vendor and service provider management',
                'network intelligence'
            ],
            'data_types': ['personal', 'professional', 'family', 'vendor', 'unknown']
        }
    }
    
    if memory_type not in system_info:
        supported_types = list(system_info.keys())
        raise ValueError(f"Unsupported memory type: '{memory_type}'. Supported types: {supported_types}")
    
    return system_info[memory_type]

@log_function()
async def create_unified_memory_system(**kwargs) -> dict:
    """
    Create a unified memory system with all memory types.
    
    Instantiates all memory system types in a coordinated configuration
    for complete memory management in asset management environments.
    
    Args:
        **kwargs: Common configuration parameters for all memory systems
        
    Returns:
        Dictionary containing all instantiated memory systems
        
    Example:
        >>> from memory import create_unified_memory_system
        >>> memory_systems = await create_unified_memory_system(max_items=1000)
        >>> episodic = memory_systems['episodic']
        >>> contact = memory_systems['contact']
    """
    logger.info("Creating unified memory system with all memory types")
    
    try:
        memory_systems = {
            'episodic': EpisodicMemory(**kwargs),
            'semantic': SemanticMemory(**kwargs),
            'procedural': ProceduralMemory(**kwargs),
            'contact': ContactMemory(**kwargs)
        }
        
        logger.info(f"Successfully created unified memory system with {len(memory_systems)} memory types")
        return memory_systems
        
    except Exception as e:
        logger.error(f"Failed to create unified memory system: {e}")
        raise

# Memory system factory class for usage
class MemorySystemFactory:
    """
    memory system factory for enterprise deployments.
    
    Provides memory system instantiation with
    configuration management, validation, and optimization
    for large-scale asset management deployments.
    """
    
    @staticmethod
    @log_function()
    def create_optimized_memory_config(
        total_memory_items: int = 10000,
        workload_type: str = 'balanced'
    ) -> dict:
        """
        Create optimized memory configuration for specific workloads.
        
        Args:
            total_memory_items: Total memory items across all systems
            workload_type: Workload optimization ('contact_heavy', 'episodic_heavy', 'balanced')
            
        Returns:
            Dictionary with optimized configuration for each memory system
        """
        logger.info(f"Creating optimized memory config: {workload_type}, {total_memory_items} items")
        
        if workload_type == 'contact_heavy':
            # Contact-heavy workload (investor relations focus)
            return {
                'contact': {'max_items': int(total_memory_items * 0.5)},
                'episodic': {'max_items': int(total_memory_items * 0.3)},
                'semantic': {'max_items': int(total_memory_items * 0.15)},
                'procedural': {'max_items': int(total_memory_items * 0.05)}
            }
        elif workload_type == 'episodic_heavy':
            # Episodic-heavy workload (communication tracking focus)
            return {
                'episodic': {'max_items': int(total_memory_items * 0.5)},
                'contact': {'max_items': int(total_memory_items * 0.25)},
                'semantic': {'max_items': int(total_memory_items * 0.15)},
                'procedural': {'max_items': int(total_memory_items * 0.1)}
            }
        else:  # balanced
            # Balanced workload
            return {
                'contact': {'max_items': int(total_memory_items * 0.3)},
                'episodic': {'max_items': int(total_memory_items * 0.3)},
                'semantic': {'max_items': int(total_memory_items * 0.25)},
                'procedural': {'max_items': int(total_memory_items * 0.15)}
            } 