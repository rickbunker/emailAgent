"""
Unit tests for the configuration system.

Tests the email agent configuration loading, validation, and error handling.
"""

# # Standard library imports
# Standard library imports
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# # Third-party imports
# Third-party imports
import pytest

# # Local application imports
# Local application imports
from src.utils.config import EmailAgentConfig, load_config


class TestEmailAgentConfig:
    """Test cases for EmailAgentConfig class."""

    def test_config_from_env_defaults(self):
        """Test that configuration loads with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = EmailAgentConfig.from_env()

            assert config.qdrant_host == "localhost"
            assert config.qdrant_port == 6333
            assert config.flask_port == 5001
            assert config.debug is False
            assert config.log_level == "INFO"
            assert config.default_hours_back == 24

    def test_config_from_env_custom_values(self):
        """Test that configuration loads custom environment values."""
        test_env = {
            "QDRANT_HOST": "test-qdrant",
            "QDRANT_PORT": "9999",
            "FLASK_PORT": "8080",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "DEFAULT_HOURS_BACK": "48",
        }

        with patch.dict(os.environ, test_env, clear=True):
            config = EmailAgentConfig.from_env()

            assert config.qdrant_host == "test-qdrant"
            assert config.qdrant_port == 9999
            assert config.flask_port == 8080
            assert config.debug is True
            assert config.log_level == "DEBUG"
            assert config.default_hours_back == 48

    def test_config_validation_valid(self):
        """Test that valid configuration passes validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create dummy credential files
            gmail_creds = Path(temp_dir) / "gmail_creds.json"
            msgraph_creds = Path(temp_dir) / "msgraph_creds.json"
            gmail_creds.touch()
            msgraph_creds.touch()

            test_env = {
                "GMAIL_CREDENTIALS_PATH": str(gmail_creds),
                "MSGRAPH_CREDENTIALS_PATH": str(msgraph_creds),
                "LOW_CONFIDENCE_THRESHOLD": "0.7",
                "REQUIRES_REVIEW_THRESHOLD": "0.5",
            }

            with patch.dict(os.environ, test_env, clear=True):
                config = EmailAgentConfig.from_env()
                errors = config.validate()

                # Should have no errors (or only missing directories that we can create)
                credential_errors = [e for e in errors if "credentials" in e.lower()]
                assert len(credential_errors) == 0

    def test_config_validation_invalid_thresholds(self):
        """Test that invalid threshold values are caught."""
        test_env = {
            "LOW_CONFIDENCE_THRESHOLD": "1.5",  # Invalid: > 1.0
            "REQUIRES_REVIEW_THRESHOLD": "-0.1",  # Invalid: < 0.0
        }

        with patch.dict(os.environ, test_env, clear=True):
            config = EmailAgentConfig.from_env()
            errors = config.validate()

            threshold_errors = [e for e in errors if "threshold" in e.lower()]
            assert len(threshold_errors) >= 2

    def test_config_is_production(self):
        """Test production mode detection."""
        with patch.dict(os.environ, {"FLASK_ENV": "production"}, clear=True):
            config = EmailAgentConfig.from_env()
            assert config.is_production() is True

        with patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=True):
            config = EmailAgentConfig.from_env()
            assert config.is_production() is False

    def test_config_get_credential_path(self):
        """Test credential path retrieval."""
        test_env = {
            "GMAIL_CREDENTIALS_PATH": "/test/gmail.json",
            "MSGRAPH_CREDENTIALS_PATH": "/test/msgraph.json",
        }

        with patch.dict(os.environ, test_env, clear=True):
            config = EmailAgentConfig.from_env()

            assert config.get_credential_path("gmail") == "/test/gmail.json"
            assert config.get_credential_path("msgraph") == "/test/msgraph.json"

            with pytest.raises(ValueError):
                config.get_credential_path("invalid_service")


class TestLoadConfig:
    """Test cases for the load_config function."""

    def test_load_config_success(self):
        """Test that load_config returns a valid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create dummy credential files
            gmail_creds = Path(temp_dir) / "gmail_creds.json"
            msgraph_creds = Path(temp_dir) / "msgraph_creds.json"
            gmail_creds.touch()
            msgraph_creds.touch()

            test_env = {
                "GMAIL_CREDENTIALS_PATH": str(gmail_creds),
                "MSGRAPH_CREDENTIALS_PATH": str(msgraph_creds),
                "FLASK_ENV": "development",  # Don't fail on validation errors
            }

            with patch.dict(os.environ, test_env, clear=True):
                config = load_config()

                assert isinstance(config, EmailAgentConfig)
                assert config.gmail_credentials_path == str(gmail_creds)

    def test_load_config_production_validation_failure(self):
        """Test that load_config raises error in production with validation failures."""
        test_env = {
            "FLASK_ENV": "production",
            "GMAIL_CREDENTIALS_PATH": "/nonexistent/gmail.json",
            "MSGRAPH_CREDENTIALS_PATH": "/nonexistent/msgraph.json",
        }

        with patch.dict(os.environ, test_env, clear=True), pytest.raises(
            RuntimeError, match="Configuration validation failed"
        ):
            load_config()
