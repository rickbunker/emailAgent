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
from datetime import datetime
from pathlib import Path
from typing import Any

# # Local application imports
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)

# Create memory data directory
MEMORY_DATA_DIR = Path("data/memory")
MEMORY_DATA_DIR.mkdir(parents=True, exist_ok=True)


def json_serialize(obj):
    """Custom JSON serializer to handle datetime and bytes objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return f"<bytes: {len(obj)} bytes>"  # Don't store actual bytes content
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


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
        logger.info(f"Loading semantic memory from: {self.file_path}")
        logger.info(f"File exists: {self.file_path.exists()}")

        if self.file_path.exists():
            try:
                logger.info(f"File size: {self.file_path.stat().st_size} bytes")
                with open(self.file_path) as f:
                    data = json.load(f)
                asset_count = len(data.get("asset_profiles", {}))
                logger.info(
                    f"Successfully loaded semantic memory with {asset_count} assets"
                )
                logger.info(f"Asset IDs: {list(data.get('asset_profiles', {}).keys())}")
                return data
            except Exception as e:
                logger.error(f"Failed to load semantic memory: {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                logger.info("Falling back to default data")
                return self._get_default_data()
        else:
            logger.warning("Semantic memory file does not exist, using default data")
            return self._get_default_data()

    def _get_default_data(self) -> dict[str, Any]:
        """Get default semantic memory data"""
        return {
            "asset_profiles": {
                "SAMPLE_ASSET": {
                    "name": "Sample Investment Asset",
                    "keywords": ["sample", "investment", "asset"],
                    "confidence": 0.8,
                }
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
            # Check if query term matches asset keywords or name
            score = 0.0

            # Check if query is in any keyword
            for keyword in profile.get("keywords", []):
                if query_lower in keyword.lower():
                    score += 0.5  # Strong match when query is in keyword

            # Check if query is in asset name
            asset_name = profile.get("name", "").lower()
            if query_lower in asset_name:
                score += 0.5  # Strong match when query is in name

            # Also give partial credit for individual word matches
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 1:  # Skip single letters
                    for keyword in profile.get("keywords", []):
                        if (
                            word in keyword.lower()
                            and query_lower not in keyword.lower()
                        ):
                            score += 0.1  # Partial match for individual words
                    if word in asset_name and query_lower not in asset_name:
                        score += 0.1

            if score > 0:
                results.append(
                    {"asset_id": asset_id, "profile": profile, "score": min(score, 1.0)}
                )

        # Sort by score and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    @log_function()
    def get_file_type_rules(self, file_extension: str) -> dict[str, Any] | None:
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
    def get_sender_mapping(self, email: str) -> dict[str, Any] | None:
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
    def get_organization_data(self, organization: str) -> dict[str, Any] | None:
        """Get organization contact data"""
        return self.data.get("organization_contacts", {}).get(organization)

    @log_function()
    def reset_to_base_state(self) -> int:
        """Reset semantic memory to base state, returns count of items reset."""
        old_count = len(self.data.get("asset_profiles", {})) + len(
            self.data.get("sender_mappings", {})
        )
        self.data = self._get_default_data()
        self._save_data()
        logger.info("Semantic memory reset to base state")
        return old_count


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

    @log_function()
    def reset_to_base_state(self) -> int:
        """Reset procedural memory to base state, returns count of rules reset."""
        old_count = (
            len(self.data.get("relevance_rules", []))
            + len(self.data.get("asset_matching_rules", []))
            + len(self.data.get("file_processing_rules", []))
        )
        self.data = self._get_default_data()
        self._save_data()
        logger.info("Procedural memory reset to base state")
        return old_count


class SimpleEpisodicMemory:
    """
    Episodic Memory using SQLite database.

    Stores processing history, human feedback, and learning experiences.
    """

    def __init__(self):
        """Initialize the episodic memory database"""
        self.db_path = MEMORY_DATA_DIR / "episodic_memory.db"
        MEMORY_DATA_DIR.mkdir(exist_ok=True)
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
        """
        Initialize the SQLite database schema.

        CRITICAL: This schema MUST be maintained when reset scripts are updated!

        Key points:
        - Uses 'created_at' column (NOT 'timestamp')
        - Any reset/migration scripts must preserve this schema
        - See reset_all_memory_to_baseline() function for proper reset procedure
        """
        with self._get_connection() as conn:
            # Check if we need to migrate old schema (timestamp -> created_at)
            cursor = conn.cursor()

            # Check if tables exist and have correct schema
            cursor.execute("PRAGMA table_info(processing_history)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            # If table doesn't exist or has wrong schema, recreate it
            if not columns or "created_at" not in columns:
                logger.warning("Migrating episodic memory database schema")

                # Backup existing data if present
                existing_data = []
                if "timestamp" in columns:
                    # Migration from old schema
                    cursor.execute("SELECT * FROM processing_history")
                    existing_data = cursor.fetchall()
                    logger.info(
                        f"Backing up {len(existing_data)} records during schema migration"
                    )

                # Drop and recreate with correct schema
                conn.execute("DROP TABLE IF EXISTS processing_history")
                conn.execute("DROP TABLE IF EXISTS human_feedback")

            # Create tables with correct schema
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
            logger.info(
                "Episodic memory database schema initialized/migrated successfully"
            )

    @log_function()
    def validate_schema(self) -> dict[str, Any]:
        """
        Validate the database schema and return diagnostic information.

        This method helps debug schema issues and ensures the database
        has the correct structure for decision reasoning functionality.

        Returns:
            Dictionary with schema validation results
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check processing_history table schema
                cursor.execute("PRAGMA table_info(processing_history)")
                processing_columns = {row[1]: row[2] for row in cursor.fetchall()}

                # Check human_feedback table schema
                cursor.execute("PRAGMA table_info(human_feedback)")
                feedback_columns = {row[1]: row[2] for row in cursor.fetchall()}

                # Count records
                cursor.execute("SELECT COUNT(*) FROM processing_history")
                processing_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM human_feedback")
                feedback_count = cursor.fetchone()[0]

                # Validate expected columns
                expected_processing_cols = {
                    "id",
                    "email_id",
                    "sender",
                    "subject",
                    "asset_id",
                    "category",
                    "confidence",
                    "decision",
                    "created_at",
                    "metadata",
                }
                expected_feedback_cols = {
                    "id",
                    "email_id",
                    "original_decision",
                    "corrected_decision",
                    "feedback_type",
                    "confidence_impact",
                    "created_at",
                    "notes",
                }

                validation_result = {
                    "schema_valid": True,
                    "processing_history": {
                        "columns": processing_columns,
                        "expected_columns": list(expected_processing_cols),
                        "missing_columns": list(
                            expected_processing_cols - set(processing_columns.keys())
                        ),
                        "has_created_at": "created_at" in processing_columns,
                        "has_timestamp": "timestamp"
                        in processing_columns,  # Should be False
                        "record_count": processing_count,
                    },
                    "human_feedback": {
                        "columns": feedback_columns,
                        "expected_columns": list(expected_feedback_cols),
                        "missing_columns": list(
                            expected_feedback_cols - set(feedback_columns.keys())
                        ),
                        "has_created_at": "created_at" in feedback_columns,
                        "has_timestamp": "timestamp"
                        in feedback_columns,  # Should be False
                        "record_count": feedback_count,
                    },
                    "database_path": str(self.db_path),
                    "database_exists": self.db_path.exists(),
                    "database_size_bytes": (
                        self.db_path.stat().st_size if self.db_path.exists() else 0
                    ),
                }

                # Check for schema issues
                schema_issues = []
                if "created_at" not in processing_columns:
                    schema_issues.append("processing_history missing created_at column")
                if "created_at" not in feedback_columns:
                    schema_issues.append("human_feedback missing created_at column")
                if "timestamp" in processing_columns:
                    schema_issues.append(
                        "processing_history has deprecated timestamp column"
                    )
                if "timestamp" in feedback_columns:
                    schema_issues.append(
                        "human_feedback has deprecated timestamp column"
                    )

                validation_result["schema_issues"] = schema_issues
                validation_result["schema_valid"] = len(schema_issues) == 0

                logger.info(
                    f"Schema validation complete: {'VALID' if validation_result['schema_valid'] else 'INVALID'}"
                )
                if schema_issues:
                    logger.warning(f"Schema issues found: {schema_issues}")

                return validation_result

        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {
                "schema_valid": False,
                "error": str(e),
                "database_path": str(self.db_path),
                "database_exists": (
                    self.db_path.exists() if hasattr(self, "db_path") else False
                ),
            }

    @log_function()
    def add_processing_record(
        self,
        email_id: str,
        sender: str,
        subject: str,
        asset_id: str,
        confidence: float,
        decision: str,
        metadata: dict[str, Any] = None,
        category: str = None,  # Optional for backward compatibility
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
                    category,  # Will be None if not provided
                    confidence,
                    decision,
                    json.dumps(metadata or {}, default=json_serialize),
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
            cursor = conn.execute(  # nosec B608
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
            cursor = conn.execute(  # nosec B608
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

    @log_function()
    def get_processing_episodes(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get processing episodes from episodic memory"""
        return self.search_similar_cases(limit=limit)

    @log_function()
    def clear_all_data(self) -> int:
        """Clear all data from episodic memory tables. Returns count of deleted records."""
        deleted_count = 0

        with self._get_connection() as conn:
            # Count records before deletion
            cursor = conn.execute("SELECT COUNT(*) FROM processing_history")
            deleted_count += cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM human_feedback")
            deleted_count += cursor.fetchone()[0]

            # Clear all tables
            conn.execute("DELETE FROM processing_history")
            conn.execute("DELETE FROM human_feedback")
            conn.commit()

        logger.info(f"Cleared all episodic memory data: {deleted_count} records")
        return deleted_count

    @log_function()
    def get_recent_records(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Get recent processing records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent processing records with metadata
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT email_id, sender, subject, asset_id, category, confidence,
                           decision, created_at, metadata
                    FROM processing_history
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

                records = []
                for row in cursor.fetchall():
                    (
                        email_id,
                        sender,
                        subject,
                        asset_id,
                        category,
                        confidence,
                        decision,
                        created_at,
                        metadata_json,
                    ) = row

                    # Parse metadata JSON
                    metadata = {}
                    if metadata_json:
                        try:
                            metadata = json.loads(metadata_json)
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse metadata JSON for record {email_id}"
                            )

                    records.append(
                        {
                            "email_id": email_id,
                            "sender": sender,
                            "subject": subject,
                            "asset_id": asset_id,
                            "category": category,
                            "confidence": confidence,
                            "decision": decision,
                            "timestamp": created_at,  # Map created_at to timestamp for consistency
                            "metadata": metadata,
                        }
                    )

                return records

        except Exception as e:
            logger.error(f"Failed to get recent records: {e}")
            return []

    @log_function()
    def find_records_by_filename(
        self, filename: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Find processing records that mention a specific filename.

        Args:
            filename: The filename to search for
            limit: Maximum number of records to return

        Returns:
            List of matching processing records
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT email_id, sender, subject, asset_id, category, confidence,
                           decision, created_at, metadata
                    FROM processing_history
                    WHERE metadata LIKE ? OR subject LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (f"%{filename}%", f"%{filename}%", limit),
                )

                records = []
                for row in cursor.fetchall():
                    (
                        email_id,
                        sender,
                        subject,
                        asset_id,
                        category,
                        confidence,
                        decision,
                        created_at,
                        metadata_json,
                    ) = row

                    # Parse metadata JSON
                    metadata = {}
                    if metadata_json:
                        try:
                            metadata = json.loads(metadata_json)
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse metadata JSON for record {email_id}"
                            )

                    records.append(
                        {
                            "email_id": email_id,
                            "sender": sender,
                            "subject": subject,
                            "asset_id": asset_id,
                            "category": category,
                            "confidence": confidence,
                            "decision": decision,
                            "timestamp": created_at,  # Map created_at to timestamp for consistency
                            "metadata": metadata,
                        }
                    )

                return records

        except Exception as e:
            logger.error(f"Failed to find records by filename: {e}")
            return []


# Memory Management and Backup Functions


@log_function()
def create_memory_backup(backup_name: str = None) -> dict[str, str]:
    """
    Create a comprehensive backup of all memory systems.

    Args:
        backup_name: Optional name for the backup (defaults to timestamp)

    Returns:
        Dictionary mapping memory type to backup file path
    """
    if backup_name is None:
        backup_name = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_dir = MEMORY_DATA_DIR / "backups" / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_paths = {}

    # Backup semantic memory
    semantic_path = MEMORY_DATA_DIR / "semantic_memory.json"
    if semantic_path.exists():
        backup_semantic = backup_dir / "semantic_memory.json"
        backup_semantic.write_text(semantic_path.read_text())
        backup_paths["semantic"] = str(backup_semantic)
        logger.info(f"Backed up semantic memory to: {backup_semantic}")

    # Backup procedural memory
    procedural_path = MEMORY_DATA_DIR / "procedural_memory.json"
    if procedural_path.exists():
        backup_procedural = backup_dir / "procedural_memory.json"
        backup_procedural.write_text(procedural_path.read_text())
        backup_paths["procedural"] = str(backup_procedural)
        logger.info(f"Backed up procedural memory to: {backup_procedural}")

    # Backup episodic memory (export SQLite to JSON)
    episodic_db_path = MEMORY_DATA_DIR / "episodic_memory.db"
    if episodic_db_path.exists():
        backup_episodic = backup_dir / "episodic_memory.json"
        episodic_data = export_episodic_memory_to_json()
        backup_episodic.write_text(
            json.dumps(episodic_data, indent=2, default=json_serialize)
        )
        backup_paths["episodic"] = str(backup_episodic)
        logger.info(f"Backed up episodic memory to: {backup_episodic}")

    # Copy the actual SQLite database as well
    if episodic_db_path.exists():
        backup_db = backup_dir / "episodic_memory.db"
        backup_db.write_bytes(episodic_db_path.read_bytes())
        backup_paths["episodic_db"] = str(backup_db)

    # Create backup manifest
    manifest = {
        "backup_name": backup_name,
        "created_at": datetime.now().isoformat(),
        "files": backup_paths,
        "version": "1.0",
    }

    manifest_path = backup_dir / "backup_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    backup_paths["manifest"] = str(manifest_path)

    logger.info(f"Created complete memory backup: {backup_name}")
    return backup_paths


@log_function()
def restore_memory_from_backup(backup_name: str) -> dict[str, bool]:
    """
    Restore all memory systems from a backup.

    Args:
        backup_name: Name of the backup to restore

    Returns:
        Dictionary mapping memory type to success status
    """
    backup_dir = MEMORY_DATA_DIR / "backups" / backup_name

    if not backup_dir.exists():
        logger.error(f"Backup directory not found: {backup_dir}")
        return {}

    manifest_path = backup_dir / "backup_manifest.json"
    if not manifest_path.exists():
        logger.error(f"Backup manifest not found: {manifest_path}")
        return {}

    # Load manifest
    manifest = json.loads(manifest_path.read_text())
    logger.info(
        f"Restoring memory backup: {backup_name} (created: {manifest.get('created_at')})"
    )

    restore_results = {}

    # Restore semantic memory
    semantic_backup = backup_dir / "semantic_memory.json"
    if semantic_backup.exists():
        try:
            semantic_path = MEMORY_DATA_DIR / "semantic_memory.json"
            semantic_path.write_text(semantic_backup.read_text())
            restore_results["semantic"] = True
            logger.info("Restored semantic memory")
        except Exception as e:
            logger.error(f"Failed to restore semantic memory: {e}")
            restore_results["semantic"] = False

    # Restore procedural memory
    procedural_backup = backup_dir / "procedural_memory.json"
    if procedural_backup.exists():
        try:
            procedural_path = MEMORY_DATA_DIR / "procedural_memory.json"
            procedural_path.write_text(procedural_backup.read_text())
            restore_results["procedural"] = True
            logger.info("Restored procedural memory")
        except Exception as e:
            logger.error(f"Failed to restore procedural memory: {e}")
            restore_results["procedural"] = False

    # Restore episodic memory database
    episodic_backup = backup_dir / "episodic_memory.db"
    if episodic_backup.exists():
        try:
            episodic_path = MEMORY_DATA_DIR / "episodic_memory.db"
            episodic_path.write_bytes(episodic_backup.read_bytes())
            restore_results["episodic"] = True
            logger.info("Restored episodic memory database")
        except Exception as e:
            logger.error(f"Failed to restore episodic memory: {e}")
            restore_results["episodic"] = False

    logger.info(
        f"Memory restore complete: {sum(restore_results.values())}/{len(restore_results)} systems restored"
    )
    return restore_results


@log_function()
def export_episodic_memory_to_json() -> dict[str, Any]:
    """
    Export episodic memory database to JSON format.

    Returns:
        Dictionary containing all episodic memory data
    """
    db_path = MEMORY_DATA_DIR / "episodic_memory.db"

    if not db_path.exists():
        logger.warning("Episodic memory database not found")
        return {"processing_history": [], "human_feedback": []}

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # Export processing history
        processing_history = []
        for row in conn.execute("SELECT * FROM processing_history ORDER BY created_at"):
            record = dict(row)
            # Parse metadata JSON if it exists
            if record.get("metadata"):
                try:
                    record["metadata"] = json.loads(record["metadata"])
                except (json.JSONDecodeError, TypeError):
                    record["metadata"] = {}
            processing_history.append(record)

        # Export human feedback
        human_feedback = []
        for row in conn.execute("SELECT * FROM human_feedback ORDER BY created_at"):
            human_feedback.append(dict(row))

        logger.info(
            f"Exported {len(processing_history)} processing records and {len(human_feedback)} feedback records"
        )

        return {
            "processing_history": processing_history,
            "human_feedback": human_feedback,
            "_metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0",
                "total_records": len(processing_history) + len(human_feedback),
            },
        }


@log_function()
def reset_all_memory_to_baseline() -> dict[str, int]:
    """
    Reset all memory systems to their baseline state.

    CRITICAL RESET REQUIREMENTS:
    ============================

    This function is called by the web UI reset buttons and MUST preserve
    the correct database schema for episodic memory!

    Key requirements:
    1. Episodic memory uses 'created_at' column (NOT 'timestamp')
    2. SimpleEpisodicMemory.__init__() will auto-migrate schema if needed
    3. Any changes to episodic schema MUST be reflected in _init_database()
    4. Frontend depends on decision_reasoning being available after reset

    Schema Dependencies:
    - UI review modal expects decision_reasoning from episodic records
    - Asset matcher stores reasoning in episodic memory
    - Database queries use created_at but map to timestamp in API responses

    DO NOT modify this function without checking:
    - SimpleEpisodicMemory._init_database() schema
    - Frontend attachments page review functionality
    - API endpoint /api/attachments/review/{asset_id}/{filename}

    Returns:
        Dictionary mapping memory type to number of items reset
    """
    reset_counts = {}

    # Reset semantic memory to baseline
    baseline_semantic = MEMORY_DATA_DIR / "semantic_memory_baseline.json"
    if baseline_semantic.exists():
        try:
            current_semantic = MEMORY_DATA_DIR / "semantic_memory.json"
            current_semantic.write_text(baseline_semantic.read_text())

            # Count items in baseline
            baseline_data = json.loads(baseline_semantic.read_text())
            item_count = len(baseline_data.get("asset_profiles", {})) + len(
                baseline_data.get("sender_mappings", {})
            )
            reset_counts["semantic"] = item_count
            logger.info(f"Reset semantic memory to baseline ({item_count} items)")
        except Exception as e:
            logger.error(f"Failed to reset semantic memory to baseline: {e}")
            reset_counts["semantic"] = 0

    # Reset procedural memory to baseline
    baseline_procedural = MEMORY_DATA_DIR / "procedural_memory_baseline.json"
    if baseline_procedural.exists():
        try:
            current_procedural = MEMORY_DATA_DIR / "procedural_memory.json"
            current_procedural.write_text(baseline_procedural.read_text())

            # Count rules in baseline
            baseline_data = json.loads(baseline_procedural.read_text())
            rule_count = (
                len(baseline_data.get("relevance_rules", []))
                + len(baseline_data.get("asset_matching_rules", []))
                + len(baseline_data.get("file_processing_rules", []))
            )
            reset_counts["procedural"] = rule_count
            logger.info(f"Reset procedural memory to baseline ({rule_count} rules)")
        except Exception as e:
            logger.error(f"Failed to reset procedural memory to baseline: {e}")
            reset_counts["procedural"] = 0

    # Reset episodic memory with proper schema handling
    # CRITICAL: This ensures correct 'created_at' schema is maintained
    try:
        logger.info("Resetting episodic memory with schema validation")

        # Delete the database file to ensure clean reset with correct schema
        episodic_db_path = MEMORY_DATA_DIR / "episodic_memory.db"
        if episodic_db_path.exists():
            episodic_db_path.unlink()
            logger.info("Removed existing episodic database for clean reset")

        # Create new instance - this will initialize correct schema
        episodic = SimpleEpisodicMemory()
        reset_counts["episodic"] = 0  # Start with 0 since we're creating fresh

        # Import baseline episodic data if it exists
        baseline_episodic = MEMORY_DATA_DIR / "episodic_memory_baseline.json"
        if baseline_episodic.exists():
            baseline_data = json.loads(baseline_episodic.read_text())

            # Import baseline processing history
            for record in baseline_data.get("processing_history", []):
                episodic.add_processing_record(
                    email_id=record["email_id"],
                    sender=record["sender"],
                    subject=record["subject"],
                    asset_id=record["asset_id"],
                    confidence=record["confidence"],
                    decision=record["decision"],
                    metadata=record.get("metadata", {}),
                    category=record.get("category"),
                )
                reset_counts["episodic"] += 1

            # Import baseline human feedback
            for feedback in baseline_data.get("human_feedback", []):
                episodic.add_human_feedback(
                    email_id=feedback["email_id"],
                    original_decision=feedback["original_decision"],
                    corrected_decision=feedback["corrected_decision"],
                    feedback_type=feedback["feedback_type"],
                    confidence_impact=feedback["confidence_impact"],
                    notes=feedback.get("notes"),
                )
                reset_counts["episodic"] += 1

            logger.info(
                f"Imported baseline episodic memory data ({reset_counts['episodic']} records)"
            )

    except Exception as e:
        logger.error(f"Failed to reset episodic memory: {e}")
        reset_counts["episodic"] = 0

    total_reset = sum(reset_counts.values())
    logger.info(f"Reset all memory systems to baseline ({total_reset} total items)")
    return reset_counts


@log_function()
def export_all_memory_to_github_format() -> dict[str, str]:
    """
    Export all memory systems in a format suitable for GitHub version control.

    Returns:
        Dictionary mapping memory type to export file path
    """
    export_paths = {}

    # Ensure current files are present and formatted nicely

    # Semantic memory - already in good JSON format
    semantic_path = MEMORY_DATA_DIR / "semantic_memory.json"
    if semantic_path.exists():
        try:
            # Re-format for consistent formatting
            data = json.loads(semantic_path.read_text())
            semantic_path.write_text(json.dumps(data, indent=2, sort_keys=True))
            export_paths["semantic"] = str(semantic_path)
            logger.info("Formatted semantic memory for GitHub")
        except Exception as e:
            logger.error(f"Failed to format semantic memory: {e}")

    # Procedural memory - already in good JSON format
    procedural_path = MEMORY_DATA_DIR / "procedural_memory.json"
    if procedural_path.exists():
        try:
            # Re-format for consistent formatting
            data = json.loads(procedural_path.read_text())
            procedural_path.write_text(json.dumps(data, indent=2, sort_keys=True))
            export_paths["procedural"] = str(procedural_path)
            logger.info("Formatted procedural memory for GitHub")
        except Exception as e:
            logger.error(f"Failed to format procedural memory: {e}")

    # Episodic memory - export to JSON for GitHub (keep SQLite for runtime)
    episodic_json_path = MEMORY_DATA_DIR / "episodic_memory_export.json"
    try:
        episodic_data = export_episodic_memory_to_json()
        episodic_json_path.write_text(
            json.dumps(episodic_data, indent=2, sort_keys=True, default=json_serialize)
        )
        export_paths["episodic_export"] = str(episodic_json_path)
        logger.info("Exported episodic memory to JSON for GitHub")
    except Exception as e:
        logger.error(f"Failed to export episodic memory: {e}")

    # Create a comprehensive memory status report
    status_path = MEMORY_DATA_DIR / "memory_status.json"
    try:
        status = {
            "last_export": datetime.now().isoformat(),
            "version": "1.0",
            "memory_systems": {
                "semantic": {
                    "file": "semantic_memory.json",
                    "baseline": "semantic_memory_baseline.json",
                    "item_count": (
                        len(
                            json.loads(semantic_path.read_text()).get(
                                "asset_profiles", {}
                            )
                        )
                        if semantic_path.exists()
                        else 0
                    ),
                },
                "procedural": {
                    "file": "procedural_memory.json",
                    "baseline": "procedural_memory_baseline.json",
                    "rule_count": (
                        (
                            len(
                                json.loads(procedural_path.read_text()).get(
                                    "relevance_rules", []
                                )
                            )
                            + len(
                                json.loads(procedural_path.read_text()).get(
                                    "asset_matching_rules", []
                                )
                            )
                            + len(
                                json.loads(procedural_path.read_text()).get(
                                    "file_processing_rules", []
                                )
                            )
                        )
                        if procedural_path.exists()
                        else 0
                    ),
                },
                "episodic": {
                    "runtime_db": "episodic_memory.db",
                    "export_json": "episodic_memory_export.json",
                    "baseline": "episodic_memory_baseline.json",
                    "record_count": len(episodic_data.get("processing_history", []))
                    + len(episodic_data.get("human_feedback", [])),
                },
            },
            "export_files": list(export_paths.keys()),
            "notes": [
                "semantic_memory.json and procedural_memory.json are the runtime files",
                "episodic_memory.db is the runtime SQLite database",
                "episodic_memory_export.json is the GitHub-friendly export",
                "*_baseline.json files contain the initial system state",
            ],
        }

        status_path.write_text(json.dumps(status, indent=2))
        export_paths["status"] = str(status_path)
        logger.info("Created memory status report")

    except Exception as e:
        logger.error(f"Failed to create memory status report: {e}")

    logger.info(f"Exported {len(export_paths)} memory files for GitHub")
    return export_paths


# Convenience function to create memory systems
def create_memory_systems() -> dict[str, Any]:
    """
    Create and return instances of all memory systems.

    Returns:
        Dictionary containing semantic, procedural, and episodic memory instances
    """
    return {
        "semantic": SimpleSemanticMemory(),
        "procedural": SimpleProceduralMemory(),
        "episodic": SimpleEpisodicMemory(),
    }
