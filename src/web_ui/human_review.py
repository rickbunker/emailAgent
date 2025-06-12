"""
Human Review System for Email Agent

Manages attachment processing items that require human review and correction.
Stores learning experiences in episodic memory to improve future matching.

Features:
    - Queue management for items needing review
    - Human correction interface
    - Episodic memory integration for learning
    - Feedback loop for system improvement

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

# Logging system
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_system import get_logger
from memory.episodic import EpisodicMemory, EpisodicMemoryType

logger = get_logger(__name__)

@dataclass
class ReviewItem:
    """Item requiring human review"""
    review_id: str
    email_id: str
    mailbox_id: str
    attachment_filename: str
    attachment_content: bytes
    email_subject: str
    email_body: str
    sender_email: str
    sender_name: Optional[str]
    email_date: str
    
    # System's analysis
    system_confidence: float
    system_asset_suggestions: List[Dict[str, Any]]
    system_reasoning: str
    document_category: Optional[str]
    confidence_level: str
    
    # Review metadata
    created_at: str
    status: str = "pending"  # pending, in_review, completed, rejected
    assigned_to: Optional[str] = None
    
    # Human correction (filled when reviewed)
    human_asset_id: Optional[str] = None
    human_document_category: Optional[str] = None
    human_reasoning: Optional[str] = None
    human_feedback: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None

class HumanReviewQueue:
    """
    Manages the queue of items requiring human review.
    
    Provides functionality for:
    - Adding items that need review
    - Retrieving items for review
    - Storing human corrections
    - Learning from corrections via episodic memory
    """
    
    def __init__(self, queue_file: str = "data/human_review_queue.json"):
        self.queue_file = Path(queue_file)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.episodic_memory = EpisodicMemory(max_items=5000)
        self._load_queue()
    
    def _load_queue(self) -> None:
        """Load review queue from disk"""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, 'r') as f:
                    data = json.load(f)
                    self.queue = data.get('items', [])
            else:
                self.queue = []
        except Exception as e:
            logger.error(f"Failed to load review queue: {e}")
            self.queue = []
    
    def _save_queue(self) -> None:
        """Save review queue to disk"""
        try:
            with open(self.queue_file, 'w') as f:
                json.dump({
                    'items': self.queue,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save review queue: {e}")
    
    def add_for_review(self, 
                      email_id: str,
                      mailbox_id: str,
                      attachment_data: Dict[str, Any],
                      email_data: Dict[str, Any],
                      processing_result: Any) -> str:
        """Add an attachment for human review"""
        
        review_id = str(uuid.uuid4())
        
        # Extract system suggestions from processing result
        system_suggestions = []
        if hasattr(processing_result, 'classification_metadata') and processing_result.classification_metadata:
            metadata = processing_result.classification_metadata
            if 'asset_matches' in metadata:
                for match in metadata['asset_matches'][:3]:  # Top 3 suggestions
                    system_suggestions.append({
                        'asset_id': match[0],
                        'confidence': match[1],
                        'reasoning': f"Pattern match confidence: {match[1]:.2f}"
                    })
        
        # Create review item
        review_item = ReviewItem(
            review_id=review_id,
            email_id=email_id,
            mailbox_id=mailbox_id,
            attachment_filename=attachment_data.get('filename', 'unknown'),
            attachment_content=attachment_data.get('content', b''),
            email_subject=email_data.get('subject', ''),
            email_body=email_data.get('body', ''),
            sender_email=email_data.get('sender_email', ''),
            sender_name=email_data.get('sender_name'),
            email_date=email_data.get('date', datetime.now(timezone.utc).isoformat()),
            system_confidence=getattr(processing_result, 'asset_confidence', 0.0),
            system_asset_suggestions=system_suggestions,
            system_reasoning=getattr(processing_result, 'classification_metadata', {}).get('reasoning', 'Automated analysis'),
            document_category=getattr(processing_result, 'document_category').value if hasattr(processing_result, 'document_category') and processing_result.document_category else None,
            confidence_level=getattr(processing_result, 'confidence_level').value if hasattr(processing_result, 'confidence_level') and processing_result.confidence_level else 'unknown',
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Convert to dict for JSON storage (excluding binary content for now)
        review_dict = asdict(review_item)
        review_dict['attachment_content'] = None  # Store separately
        
        # Save attachment content to separate file
        content_file = Path(f"data/review_attachments/{review_id}")
        content_file.parent.mkdir(parents=True, exist_ok=True)
        with open(content_file, 'wb') as f:
            f.write(review_item.attachment_content)
        
        self.queue.append(review_dict)
        self._save_queue()
        
        logger.info(f"Added item for human review: {review_item.attachment_filename} (ID: {review_id})")
        return review_id
    
    def get_pending_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get items pending review"""
        pending = [item for item in self.queue if item['status'] == 'pending']
        return pending[:limit]
    
    def get_item(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Get specific review item"""
        for item in self.queue:
            if item['review_id'] == review_id:
                # Load attachment content
                content_file = Path(f"data/review_attachments/{review_id}")
                if content_file.exists():
                    with open(content_file, 'rb') as f:
                        item['attachment_content'] = f.read()
                return item
        return None
    
    async def submit_review(self, 
                           review_id: str,
                           human_asset_id: str,
                           human_document_category: str,
                           human_reasoning: str,
                           human_feedback: str,
                           reviewed_by: str = "human_reviewer") -> bool:
        """Submit human review and store learning"""
        
        # Find the item
        item = None
        for i, queue_item in enumerate(self.queue):
            if queue_item['review_id'] == review_id:
                item = queue_item
                break
        
        if not item:
            logger.error(f"Review item not found: {review_id}")
            return False
        
        # Update the item with human corrections
        item['human_asset_id'] = human_asset_id
        item['human_document_category'] = human_document_category
        item['human_reasoning'] = human_reasoning
        item['human_feedback'] = human_feedback
        item['reviewed_at'] = datetime.now(timezone.utc).isoformat()
        item['reviewed_by'] = reviewed_by
        item['status'] = 'completed'
        
        # Store learning in episodic memory
        await self._store_learning_experience(item)
        
        self._save_queue()
        logger.info(f"Review completed for item: {review_id}")
        return True
    
    async def _store_learning_experience(self, review_item: Dict[str, Any]) -> None:
        """Store the learning experience in episodic memory"""
        
        # Create comprehensive learning content
        learning_content = f"""
Human Review Correction - Asset Matching Learning

ORIGINAL EMAIL:
Subject: {review_item['email_subject']}
Sender: {review_item['sender_email']} ({review_item['sender_name'] or 'No name'})
Date: {review_item['email_date']}

ATTACHMENT:
Filename: {review_item['attachment_filename']}

SYSTEM ANALYSIS:
Confidence: {review_item['system_confidence']:.2f}
Document Category: {review_item['document_category'] or 'Unknown'}
Confidence Level: {review_item['confidence_level']}
System Reasoning: {review_item['system_reasoning']}

SYSTEM SUGGESTIONS:
{self._format_system_suggestions(review_item['system_asset_suggestions'])}

HUMAN CORRECTION:
Correct Asset: {review_item['human_asset_id']}
Correct Category: {review_item['human_document_category']}
Human Reasoning: {review_item['human_reasoning']}
Additional Feedback: {review_item['human_feedback']}

LEARNING INSIGHTS:
{self._generate_learning_insights(review_item)}
"""
        
        # Metadata for the learning experience
        metadata = {
            'review_id': review_item['review_id'],
            'email_id': review_item['email_id'],
            'sender_email': review_item['sender_email'],
            'attachment_filename': review_item['attachment_filename'],
            'system_confidence': review_item['system_confidence'],
            'system_category': review_item['document_category'],
            'human_asset_id': review_item['human_asset_id'],
            'human_category': review_item['human_document_category'],
            'correction_type': self._determine_correction_type(review_item),
            'confidence_gap': review_item['system_confidence'],
            'learning_priority': self._calculate_learning_priority(review_item),
            'sender_domain': review_item['sender_email'].split('@')[1] if '@' in review_item['sender_email'] else '',
            'file_extension': Path(review_item['attachment_filename']).suffix.lower(),
            'review_date': review_item['reviewed_at'],
            'reviewed_by': review_item['reviewed_by']
        }
        
        # Store in episodic memory
        try:
            await self.episodic_memory.add_feedback(
                content=learning_content,
                feedback_type="correction",
                user_id=review_item['reviewed_by'],
                context=metadata
            )
            logger.info(f"Stored learning experience for review: {review_item['review_id']}")
        except Exception as e:
            logger.error(f"Failed to store learning experience: {e}")
    
    def _format_system_suggestions(self, suggestions: List[Dict[str, Any]]) -> str:
        """Format system suggestions for learning content"""
        if not suggestions:
            return "No asset suggestions provided"
        
        formatted = []
        for i, suggestion in enumerate(suggestions, 1):
            formatted.append(f"{i}. Asset ID: {suggestion['asset_id']} (Confidence: {suggestion['confidence']:.2f})")
        
        return "\n".join(formatted)
    
    def _generate_learning_insights(self, review_item: Dict[str, Any]) -> str:
        """Generate learning insights from the correction"""
        insights = []
        
        # Filename pattern analysis
        filename = review_item['attachment_filename'].lower()
        if 'loan' in filename or 'credit' in filename:
            insights.append(f"Filename contains loan/credit indicators: '{filename}'")
        
        # Sender pattern analysis
        sender_domain = review_item['sender_email'].split('@')[1] if '@' in review_item['sender_email'] else ''
        insights.append(f"Sender domain pattern: {sender_domain}")
        
        # Subject pattern analysis
        subject = review_item['email_subject'].lower()
        insights.append(f"Subject pattern analysis: '{review_item['email_subject']}'")
        
        # Confidence gap analysis
        if review_item['system_confidence'] < 0.5:
            insights.append("Low system confidence - pattern recognition needs improvement")
        
        return "\n".join(insights)
    
    def _determine_correction_type(self, review_item: Dict[str, Any]) -> str:
        """Determine the type of correction made"""
        if not review_item['system_asset_suggestions']:
            return "no_suggestions_provided"
        elif review_item['human_asset_id'] in [s['asset_id'] for s in review_item['system_asset_suggestions']]:
            return "selected_from_suggestions"
        else:
            return "completely_different_asset"
    
    def _calculate_learning_priority(self, review_item: Dict[str, Any]) -> str:
        """Calculate learning priority based on correction type"""
        if review_item['system_confidence'] > 0.7:
            return "high"  # System was confident but wrong
        elif review_item['system_confidence'] > 0.4:
            return "medium"
        else:
            return "low"  # System wasn't confident anyway
    
    def get_stats(self) -> Dict[str, Any]:
        """Get review queue statistics"""
        total = len(self.queue)
        pending = sum(1 for item in self.queue if item['status'] == 'pending')
        completed = sum(1 for item in self.queue if item['status'] == 'completed')
        in_review = sum(1 for item in self.queue if item['status'] == 'in_review')
        
        return {
            'total_items': total,
            'pending': pending,
            'completed': completed,
            'in_review': in_review,
            'completion_rate': (completed / total * 100) if total > 0 else 0
        }

# Global review queue instance
review_queue = HumanReviewQueue() 