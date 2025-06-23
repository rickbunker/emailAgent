# Episodic Memory Policy

## Core Principle
**NOTHING goes into episodic memory without explicit human review and approval.**

## What is Episodic Memory?
Episodic memory stores validated experiences from processing emails and attachments. It serves as the system's learning history, allowing it to improve over time based on human-validated experiences.

## What Was Fixed

### 1. Disabled Automatic Recording in Asset Matcher
- The `_record_matching_session` method was already commented out (line 113 of `asset_matcher.py`)
- This prevents automatic recording of asset matches to episodic memory

### 2. Fixed Feedback Integrator
- Added check in `integrate_feedback` to prevent automatic recording when `feedback_type == "human_review_required"`
- This flag is just an indicator that review is needed, not actual human feedback
- Only real human feedback (with corrections, reasons, etc.) should be recorded

### 3. Cleaned Episodic Memory Database
- Removed all 42 polluted records that were automatically generated
- Database now starts clean with proper schema
- Tables: `processing_history` and `human_feedback`

## Proper Usage

### When to Write to Episodic Memory
1. **Human validates a match**: Record the validated match with confidence scores
2. **Human corrects a mistake**: Record both original and corrected decision
3. **Human provides improvement feedback**: Record specific improvements

### What Should Be Recorded
- Email metadata (id, sender, subject)
- Asset matches with human-validated confidence
- Decision factors that led to the match
- Human corrections and reasoning
- Learning signals for future improvement

### What Should NOT Be Recorded
- Automatic processing without human validation
- "Needs review" flags
- Temporary processing states
- Unvalidated matches or decisions

## Implementation Details

The feedback integrator now returns early when it encounters automatic flags:
```python
if feedback_type == "human_review_required":
    return {
        "status": "awaiting_human_feedback",
        "memory_updates": {},
        "learning_impact": {"expected_accuracy_improvement": 0.0},
    }
```

This ensures episodic memory remains a clean, human-validated learning repository that the system can trust for future decision-making.
