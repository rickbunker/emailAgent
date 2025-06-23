"""
Simplified Memory System Implementation

Uses JSON files and SQLite for storage instead of Qdrant vector database.
This provides a simple, file-based approach for development and testing.

Storage Structure:
- Semantic Memory: data/memory/semantic_memory.json
- Procedural Memory: data/memory/procedural_memory.json
- Contact Memory: data/memory/contact_memory.json
- Episodic Memory: data/memory/episodic_memory.db (SQLite)
"""

# # Standard library imports
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

# # Local application imports
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)

# Create memory data directory
MEMORY_DATA_DIR = Path("data/memory")
MEMORY_DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class MemoryItem:
    """Base class for memory items"""

    id: str
    content: str
    metadata: dict[str, Any]
    created_at: str
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryItem":
        return cls(**data)


class SimpleSemanticMemory:
    """
    Semantic Memory using JSON file storage.

    Stores asset profiles, keywords, patterns, and factual knowledge.
    """

    def __init__(self):
        self.file_path = MEMORY_DATA_DIR / "semantic_memory.json"
        self.data: dict[str, Any] = self._load_data()
        logger.info("✅ SimpleSemanticMemory initialized")

    @log_function()
    def _load_data(self) -> dict[str, Any]:
        """Load data from JSON file"""
        if self.file_path.exists():
            try:
                with open(self.file_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load semantic memory: {e}")
                return self._get_default_data()
        else:
            return self._get_default_data()

    def _get_default_data(self) -> dict[str, Any]:
        """Get default semantic memory data"""
        return {
            "asset_profiles": {
                "SAMPLE_ASSET": {
                    "name": "Sample Investment Asset",
                    "keywords": ["sample", "investment", "asset"],
                    "document_types": ["financial", "report", "statement"],
                    "confidence": 0.8,
                }
            },
            "document_categories": {
                "financial": {
                    "patterns": [
                        "financial",
                        "statement",
                        "report",
                        "balance",
                        "income",
                    ],
                    "file_extensions": ["pdf", "xlsx", "docx"],
                    "confidence": 0.7,
                },
                "legal": {
                    "patterns": ["contract", "agreement", "legal", "terms"],
                    "file_extensions": ["pdf", "docx"],
                    "confidence": 0.8,
                },
            },
            "file_type_rules": {
                "pdf": {"allowed": True, "max_size_mb": 50},
                "xlsx": {"allowed": True, "max_size_mb": 25},
                "docx": {"allowed": True, "max_size_mb": 25},
                "jpg": {"allowed": True, "max_size_mb": 10},
                "png": {"allowed": True, "max_size_mb": 10},
            },
            "sender_mappings": {
                "advisor@example.com": {
                    "name": "Investment Advisor",
                    "asset_ids": ["SAMPLE_ASSET"],
                    "trust_score": 0.9,
                    "organization": "Example Investment Co",
                    "relationship_type": "advisor",
                }
            },
            "organization_contacts": {
                "Example Investment Co": {
                    "domain": "example.com",
                    "trust_score": 0.8,
                    "contact_count": 1,
                    "asset_ids": ["SAMPLE_ASSET"],
                }
            },
        }

    @log_function()
    def _save_data(self):
        """Save data to JSON file"""
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save semantic memory: {e}")

    @log_function()
    def search_asset_profiles(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search for asset profiles matching the query"""
        results = []
        query_lower = query.lower()

        for asset_id, profile in self.data.get("asset_profiles", {}).items():
            # Simple keyword matching
            score = 0.0
            for keyword in profile.get("keywords", []):
                if keyword.lower() in query_lower:
                    score += 0.3

            if profile.get("name", "").lower() in query_lower:
                score += 0.5

            if score > 0:
                results.append(
                    {"asset_id": asset_id, "profile": profile, "score": min(score, 1.0)}
                )

        # Sort by score and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    @log_function()
    def search_document_categories(self, query: str) -> list[dict[str, Any]]:
        """Search for document categories matching the query"""
        results = []
        query_lower = query.lower()

        for category, info in self.data.get("document_categories", {}).items():
            score = 0.0
            for pattern in info.get("patterns", []):
                if pattern.lower() in query_lower:
                    score += 0.4

            if score > 0:
                results.append(
                    {"category": category, "info": info, "score": min(score, 1.0)}
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    @log_function()
    def get_file_type_rules(self, file_extension: str) -> Optional[dict[str, Any]]:
        """Get file type rules for an extension"""
        return self.data.get("file_type_rules", {}).get(file_extension.lower())

    @log_function()
    def add_asset_profile(self, asset_id: str, profile: dict[str, Any]):
        """Add or update an asset profile"""
        if "asset_profiles" not in self.data:
            self.data["asset_profiles"] = {}

        self.data["asset_profiles"][asset_id] = profile
        self._save_data()
        logger.info(f"Added asset profile: {asset_id}")

    @log_function()
    def get_sender_mapping(self, email: str) -> Optional[dict[str, Any]]:
        """Get sender mapping for an email address"""
        return self.data.get("sender_mappings", {}).get(email.lower())

    @log_function()
    def search_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """Search for contacts by email domain"""
        results = []
        domain_lower = domain.lower()

        for email, contact in self.data.get("sender_mappings", {}).items():
            if domain_lower in email:
                results.append(
                    {
                        "email": email,
                        "contact": contact,
                        "score": 1.0 if email.endswith(domain_lower) else 0.5,
                    }
                )

        return results

    @log_function()
    def add_sender_mapping(self, email: str, contact_info: dict[str, Any]):
        """Add or update a sender mapping"""
        if "sender_mappings" not in self.data:
            self.data["sender_mappings"] = {}

        self.data["sender_mappings"][email.lower()] = contact_info
        self._save_data()
        logger.info(f"Added sender mapping: {email}")

    @log_function()
    def get_organization_data(self, organization: str) -> Optional[dict[str, Any]]:
        """Get organization contact data"""
        return self.data.get("organization_contacts", {}).get(organization)


class SimpleProceduralMemory:
    """
    Procedural Memory using JSON file storage.

    Stores business rules, processing procedures, and algorithms.
    """

    def __init__(self):
        self.file_path = MEMORY_DATA_DIR / "procedural_memory.json"
        self.data: dict[str, Any] = self._load_data()
        logger.info("✅ SimpleProceduralMemory initialized")

    def _load_data(self) -> dict[str, Any]:
        """Load data from JSON file"""
        if self.file_path.exists():
            try:
                with open(self.file_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load procedural memory: {e}")
                return self._get_default_data()
        else:
            return self._get_default_data()

    def _get_default_data(self) -> dict[str, Any]:
        """Get default procedural memory data"""
        return {
            "relevance_rules": [
                {
                    "rule_id": "investment_keywords",
                    "description": "Check for investment-related keywords",
                    "patterns": ["investment", "portfolio", "asset", "fund", "capital"],
                    "weight": 0.6,
                    "confidence": 0.8,
                },
                {
                    "rule_id": "financial_attachments",
                    "description": "Financial document attachments",
                    "patterns": ["statement", "report", "financial", "balance"],
                    "weight": 0.7,
                    "confidence": 0.9,
                },
            ],
            "asset_matching_rules": [
                {
                    "rule_id": "exact_name_match",
                    "description": "Exact asset name in filename or subject",
                    "weight": 0.9,
                    "confidence": 0.95,
                },
                {
                    "rule_id": "keyword_match",
                    "description": "Asset keywords in content",
                    "weight": 0.7,
                    "confidence": 0.8,
                },
            ],
            "file_processing_rules": [
                {
                    "rule_id": "pdf_processing",
                    "description": "PDF document processing",
                    "file_types": ["pdf"],
                    "max_size_mb": 50,
                    "extract_text": True,
                },
                {
                    "rule_id": "excel_processing",
                    "description": "Excel spreadsheet processing",
                    "file_types": ["xlsx", "xls"],
                    "max_size_mb": 25,
                    "extract_text": False,
                },
            ],
        }

    def _save_data(self):
        """Save data to JSON file"""
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save procedural memory: {e}")

    @log_function()
    def get_relevance_rules(self) -> list[dict[str, Any]]:
        """Get all relevance detection rules"""
        return self.data.get("relevance_rules", [])

    @log_function()
    def get_asset_matching_rules(self) -> list[dict[str, Any]]:
        """Get all asset matching rules"""
        return self.data.get("asset_matching_rules", [])

    @log_function()
    def get_file_processing_rules(self, file_type: str = None) -> list[dict[str, Any]]:
        """Get file processing rules, optionally filtered by file type"""
        rules = self.data.get("file_processing_rules", [])

        if file_type:
            file_type = file_type.lower()
            rules = [rule for rule in rules if file_type in rule.get("file_types", [])]

        return rules


class SimpleEpisodicMemory:
    """
    Episodic Memory using SQLite database.

    Stores processing history, human feedback, and learning experiences.
    """

    def __init__(self):
        self.db_path = MEMORY_DATA_DIR / "episodic_memory.db"
        self._init_database()
        logger.info("✅ SimpleEpisodicMemory initialized")

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Initialize the SQLite database schema"""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    subject TEXT,
                    asset_id TEXT,
                    category TEXT,
                    confidence REAL,
                    decision TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS human_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL,
                    original_decision TEXT,
                    corrected_decision TEXT,
                    feedback_type TEXT,
                    confidence_impact REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """
            )

            conn.commit()

    @log_function()
    def add_processing_record(
        self,
        email_id: str,
        sender: str,
        subject: str,
        asset_id: str,
        category: str,
        confidence: float,
        decision: str,
        metadata: dict[str, Any] = None,
    ):
        """Add a processing record to episodic memory"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO processing_history
                (email_id, sender, subject, asset_id, category, confidence, decision, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email_id,
                    sender,
                    subject,
                    asset_id,
                    category,
                    confidence,
                    decision,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()

        logger.info(f"Added processing record for email: {email_id}")

    @log_function()
    def add_human_feedback(
        self,
        email_id: str,
        original_decision: str,
        corrected_decision: str,
        feedback_type: str,
        confidence_impact: float,
        notes: str = None,
    ):
        """Add human feedback to episodic memory"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO human_feedback
                (email_id, original_decision, corrected_decision, feedback_type, confidence_impact, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    email_id,
                    original_decision,
                    corrected_decision,
                    feedback_type,
                    confidence_impact,
                    notes,
                ),
            )
            conn.commit()

        logger.info(f"Added human feedback for email: {email_id}")

    @log_function()
    def search_similar_cases(
        self,
        sender: str = None,
        asset_id: str = None,
        category: str = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for similar processing cases"""
        conditions = []
        params = []

        if sender:
            conditions.append("sender LIKE ?")
            params.append(f"%{sender}%")

        if asset_id:
            conditions.append("asset_id = ?")
            params.append(asset_id)

        if category:
            conditions.append("category = ?")
            params.append(category)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM processing_history
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """,
                params,
            )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "id": row["id"],
                        "email_id": row["email_id"],
                        "sender": row["sender"],
                        "subject": row["subject"],
                        "asset_id": row["asset_id"],
                        "category": row["category"],
                        "confidence": row["confidence"],
                        "decision": row["decision"],
                        "created_at": row["created_at"],
                        "metadata": json.loads(row["metadata"] or "{}"),
                    }
                )

            return results

    @log_function()
    def get_feedback_history(
        self, email_id: str = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get human feedback history"""
        params = []
        where_clause = ""

        if email_id:
            where_clause = "WHERE email_id = ?"
            params.append(email_id)

        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM human_feedback
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """,
                params,
            )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "id": row["id"],
                        "email_id": row["email_id"],
                        "original_decision": row["original_decision"],
                        "corrected_decision": row["corrected_decision"],
                        "feedback_type": row["feedback_type"],
                        "confidence_impact": row["confidence_impact"],
                        "created_at": row["created_at"],
                        "notes": row["notes"],
                    }
                )

            return results
