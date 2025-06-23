"""
Email Interface Factory for EmailAgent

A complete factory pattern implementation for creating email system interfaces
in private market asset management environments. Provides unified instantiation,
configuration management, and credential templates for all supported email systems.

Features:
    - Factory pattern for multiple email system types
    - Configuration-driven interface creation
    - Credential template generation for setup guidance
    - Type safety with complete validation
    - error handling and logging
    - Support for Gmail, Microsoft Graph/Office 365 systems

Business Context:
    Designed for asset management firms requiring flexible email system integration
    across different organizational infrastructures while maintaining consistent
    interface patterns and security standards.

Technical Architecture:
    - Abstract factory pattern with type-safe enum-based system selection
    - Configuration-driven instantiation with validation
    - Credential template system for deployment guidance
    - Complete error handling with business-context messaging

Supported Systems:
    - Gmail: Google Workspace integration
    - Microsoft Graph: Office 365/Exchange Online
    - Outlook: Alias for Microsoft Graph
    - Office365: Alias for Microsoft Graph

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
import os

# Logging system
import sys
from enum import Enum
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # Local application imports
from utils.logging_system import get_logger, log_function  # noqa: E402

from .base import BaseEmailInterface, EmailSystemError  # noqa: E402
from .gmail import GmailInterface  # noqa: E402
from .msgraph import MicrosoftGraphInterface  # noqa: E402

# Initialize logger
logger = get_logger(__name__)


class EmailSystemType(Enum):
    """
    Enumeration of supported email system types.

    Provides type-safe identification of email systems with aliases
    for common naming conventions in enterprise environments.

    Values:
        GMAIL: Google Workspace Gmail system
        MICROSOFT_GRAPH: Microsoft Graph API (primary)
        OUTLOOK: Alias for Microsoft Graph (legacy naming)
        OFFICE365: Alias for Microsoft Graph (common naming)
    """

    GMAIL = "gmail"
    MICROSOFT_GRAPH = "microsoft_graph"
    OUTLOOK = "outlook"  # Alias for Microsoft Graph
    OFFICE365 = "office365"  # Alias for Microsoft Graph


class EmailInterfaceFactory:
    """
    factory for creating email interface instances.

    Provides complete email system instantiation with configuration
    management, credential validation, and template generation designed
    for enterprise asset management environments.

    Features:
        - Type-safe email system creation
        - Configuration-driven instantiation
        - Credential template generation
        - Complete error handling and validation
        - Support for multiple authentication patterns

    Business Context:
        Enables asset management firms to deploy email integration across
        diverse organizational infrastructures while maintaining consistent
        security and operational standards.

    Usage:
        Direct creation:
        >>> interface = EmailInterfaceFactory.create('gmail', credentials={...})

        Configuration-driven:
        >>> config = {'type': 'microsoft_graph', 'credentials': {...}}
        >>> interface = EmailInterfaceFactory.create_from_config(config)
    """

    # System type mappings for validation and aliases
    _SYSTEM_MAPPINGS = {
        EmailSystemType.GMAIL.value: GmailInterface,
        EmailSystemType.MICROSOFT_GRAPH.value: MicrosoftGraphInterface,
        EmailSystemType.OUTLOOK.value: MicrosoftGraphInterface,
        EmailSystemType.OFFICE365.value: MicrosoftGraphInterface,
    }

    @classmethod
    @log_function()
    def create(cls, system_type: str, **kwargs) -> BaseEmailInterface:
        """
        Create an email interface instance for the specified system type.

        Instantiates the appropriate email interface implementation with
        complete validation, logging, and error handling suitable
        for production asset management environments.

        Args:
            system_type: Email system identifier ('gmail', 'microsoft_graph', 'outlook', 'office365')
            **kwargs: System-specific configuration parameters passed to interface constructor

        Returns:
            Configured email interface instance ready for connection

        Raises:
            EmailSystemError: If system type unsupported or instantiation fails
            ValueError: If system_type parameter is invalid

        Example:
            >>> # Create Gmail interface
            >>> gmail = EmailInterfaceFactory.create('gmail')
            >>>
            >>> # Create Microsoft Graph interface with credentials path
            >>> msgraph = EmailInterfaceFactory.create(
            ...     'microsoft_graph',
            ...     credentials_path='config/msgraph_creds.json'
            ... )
        """
        if not system_type or not isinstance(system_type, str):
            raise ValueError("System type must be a non-empty string")

        normalized_type = system_type.lower().strip()
        logger.info(f"Creating email interface for system type: {normalized_type}")

        try:
            # Validate system type
            if normalized_type not in cls._SYSTEM_MAPPINGS:
                supported_types = list(cls._SYSTEM_MAPPINGS.keys())
                logger.error(f"Unsupported email system type: {normalized_type}")
                raise EmailSystemError(
                    f"Unsupported email system type: '{system_type}'. "
                    f"Supported types: {supported_types}"
                )

            # Get interface class and instantiate
            interface_class = cls._SYSTEM_MAPPINGS[normalized_type]
            logger.debug(
                f"Instantiating {interface_class.__name__} with kwargs: {list(kwargs.keys())}"
            )

            interface = interface_class(**kwargs)

            logger.info(f"Successfully created {interface_class.__name__} interface")
            return interface

        except EmailSystemError:
            raise
        except Exception as e:
            logger.error(f"Failed to create email interface for {normalized_type}: {e}")
            raise EmailSystemError(
                f"Failed to create {system_type} email interface: {e}"
            ) from e

    @classmethod
    @log_function()
    def create_from_config(cls, config: dict[str, Any]) -> BaseEmailInterface:
        """
        Create an email interface from a configuration dictionary.

        Provides configuration-driven interface instantiation with complete
        validation and structured parameter extraction for deployment scenarios
        in asset management environments.

        Args:
            config: Configuration dictionary containing:
                - 'type': Email system type (required)
                - 'credentials': Authentication credentials (optional)
                - Additional system-specific settings

        Returns:
            Configured email interface instance

        Raises:
            EmailSystemError: If configuration invalid or creation fails
            ValueError: If required configuration fields missing

        Example:
            >>> config = {
            ...     'type': 'gmail',
            ...     'credentials': {
            ...         'credentials_file': 'path/to/credentials.json',
            ...         'token_file': 'path/to/token.json'
            ...     }
            ... }
            >>> interface = EmailInterfaceFactory.create_from_config(config)
        """
        if not config or not isinstance(config, dict):
            raise ValueError("Configuration must be a non-empty dictionary")

        if "type" not in config:
            logger.error("Configuration missing required 'type' field")
            raise EmailSystemError("Configuration must specify 'type' field")

        system_type = config["type"]
        logger.info(f"Creating email interface from config for type: {system_type}")

        try:
            # Extract configuration parameters
            settings = config.copy()
            settings.pop("type")

            # Log configuration structure (without sensitive data)
            config_keys = list(settings.keys())
            logger.debug(f"Configuration keys for {system_type}: {config_keys}")

            interface = cls.create(system_type, **settings)

            logger.info(
                f"Successfully created email interface from config for {system_type}"
            )
            return interface

        except Exception as e:
            logger.error(f"Failed to create interface from config: {e}")
            if isinstance(e, EmailSystemError | ValueError):
                raise
            raise EmailSystemError(
                f"Configuration-based interface creation failed: {e}"
            ) from e

    @classmethod
    @log_function()
    def get_supported_types(cls) -> list[str]:
        """
        Get complete list of supported email system types.

        Returns all supported email system identifiers including aliases
        for use in configuration validation and user interface generation.

        Returns:
            List of supported email system type strings

        Example:
            >>> types = EmailInterfaceFactory.get_supported_types()
            >>> print(types)
            ['gmail', 'microsoft_graph', 'outlook', 'office365']
        """
        supported_types = [system_type.value for system_type in EmailSystemType]
        logger.debug(f"Returning {len(supported_types)} supported email system types")
        return supported_types

    @classmethod
    @log_function()
    def get_credentials_template(cls, system_type: str) -> dict[str, Any]:
        """
        Generate credentials configuration template for specified system type.

        Provides complete credential field templates with descriptions,
        requirements, and examples to guide deployment configuration in
        asset management environments.

        Args:
            system_type: Email system identifier

        Returns:
            Dictionary containing credential field templates with metadata:
                - description: Human-readable field description
                - required: Whether field is mandatory
                - example: Example value format
                - default: Default value (if applicable)

        Raises:
            EmailSystemError: If system type unsupported

        Example:
            >>> template = EmailInterfaceFactory.get_credentials_template('gmail')
            >>> print(template['credentials_file']['description'])
            'Path to Google OAuth2 credentials.json file (for first-time auth)'
        """
        if not system_type or not isinstance(system_type, str):
            raise ValueError("System type must be a non-empty string")

        normalized_type = system_type.lower().strip()
        logger.info(
            f"Generating credentials template for system type: {normalized_type}"
        )

        if normalized_type == EmailSystemType.GMAIL.value:
            template = {
                "credentials_file": {
                    "description": "Path to Google OAuth2 credentials.json file (for first-time auth)",
                    "required": True,
                    "example": "/path/to/credentials.json",
                    "note": "Download from Google Cloud Console OAuth 2.0 Client IDs",
                },
                "token_file": {
                    "description": "Path to save/load OAuth2 token for persistent authentication",
                    "required": False,
                    "example": "/path/to/token.json",
                    "note": "Auto-created after first authentication",
                },
                "token_data": {
                    "description": "Direct token data dictionary (alternative to token_file)",
                    "required": False,
                    "example": {
                        "access_token": "ya29.a0ARrdaM...",
                        "refresh_token": "1//04...",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "client_id": "123...apps.googleusercontent.com",
                        "client_secret": "ABC...",  # pragma: allowlist secret
                        "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
                    },
                    "note": "Use for programmatic token management",
                },
            }

        elif normalized_type in [
            EmailSystemType.MICROSOFT_GRAPH.value,
            EmailSystemType.OUTLOOK.value,
            EmailSystemType.OFFICE365.value,
        ]:
            template = {
                "credentials_path": {
                    "description": "Path to Microsoft Graph credentials JSON file",
                    "required": True,
                    "example": "/path/to/msgraph_credentials.json",
                    "note": "Contains client_id, tenant_id, and application_name",
                },
                "client_id": {
                    "description": "Azure AD Application (client) ID from app registration",
                    "required": True,
                    "example": "12345678-1234-1234-1234-123456789012",
                    "note": "Found in Azure Portal > App registrations > Overview",
                },
                "tenant_id": {
                    "description": "Azure AD Directory (tenant) ID for organizational context",
                    "required": True,
                    "example": "87654321-4321-4321-4321-210987654321",
                    "note": 'Use "common" for multi-tenant, specific tenant ID for single-tenant',
                },
                "client_secret": {
                    "description": "Azure AD Client secret for confidential client applications",
                    "required": False,
                    "example": "your-client-secret-value",
                    "note": "Optional for public client (PKCE) applications",
                },
                "redirect_uri": {
                    "description": "OAuth2 redirect URI configured in Azure app registration",
                    "required": False,
                    "default": "http://localhost:8080",
                    "example": "http://localhost:8080",
                    "note": "Must match URI configured in Azure Portal",
                },
            }

        else:
            supported_types = cls.get_supported_types()
            logger.error(
                f"Unsupported system type for credentials template: {normalized_type}"
            )
            raise EmailSystemError(
                f"Unsupported email system type: '{system_type}'. "
                f"Supported types: {supported_types}"
            )

        logger.debug(
            f"Generated credentials template with {len(template)} fields for {normalized_type}"
        )
        return template

    @classmethod
    @log_function()
    def validate_credentials(
        cls, system_type: str, credentials: dict[str, Any]
    ) -> dict[str, str]:
        """
        Validate credentials configuration against system requirements.

        Performs complete validation of credential configuration
        against system-specific requirements with detailed error reporting
        for deployment troubleshooting.

        Args:
            system_type: Email system identifier
            credentials: Credentials configuration to validate

        Returns:
            Dictionary containing validation results:
                - 'status': 'valid' or 'invalid'
                - 'errors': List of validation error messages
                - 'warnings': List of validation warnings

        Raises:
            EmailSystemError: If system type unsupported

        Example:
            >>> creds = {'credentials_file': '/path/to/creds.json'}
            >>> result = EmailInterfaceFactory.validate_credentials('gmail', creds)
            >>> if result['status'] == 'valid':
            ...     print("Credentials are valid")
        """
        if not system_type or not isinstance(system_type, str):
            raise ValueError("System type must be a non-empty string")

        if not credentials or not isinstance(credentials, dict):
            raise ValueError("Credentials must be a non-empty dictionary")

        normalized_type = system_type.lower().strip()
        logger.info(f"Validating credentials for system type: {normalized_type}")

        validation_result = {"status": "valid", "errors": [], "warnings": []}

        try:
            template = cls.get_credentials_template(normalized_type)

            # Check required fields
            for field_name, field_config in template.items():
                if (
                    field_config.get("required", False)
                    and field_name not in credentials
                ):
                    validation_result["errors"].append(
                        f"Missing required field '{field_name}': {field_config['description']}"
                    )

            # Check for unknown fields (warnings)
            template_fields = set(template.keys())
            provided_fields = set(credentials.keys())
            unknown_fields = provided_fields - template_fields

            for unknown_field in unknown_fields:
                validation_result["warnings"].append(
                    f"Unknown credential field '{unknown_field}' for {system_type}"
                )

            # Set overall status
            if validation_result["errors"]:
                validation_result["status"] = "invalid"

            error_count = len(validation_result["errors"])
            warning_count = len(validation_result["warnings"])
            logger.info(
                f"Credentials validation complete: {validation_result['status']} ({error_count} errors, {warning_count} warnings)"
            )

            return validation_result

        except Exception as e:
            logger.error(f"Credentials validation failed: {e}")
            if isinstance(e, EmailSystemError):
                raise
            raise EmailSystemError(f"Credentials validation error: {e}") from e

    @classmethod
    @log_function()
    def get_system_info(cls, system_type: str) -> dict[str, Any]:
        """
        Get complete information about a specific email system type.

        Provides detailed system information including capabilities,
        requirements, and configuration guidance for deployment planning
        in asset management environments.

        Args:
            system_type: Email system identifier

        Returns:
            Dictionary containing system information:
                - name: Human-readable system name
                - description: System description and capabilities
                - authentication: Authentication method details
                - requirements: System requirements and dependencies
                - documentation: Links to relevant documentation

        Raises:
            EmailSystemError: If system type unsupported

        Example:
            >>> info = EmailInterfaceFactory.get_system_info('gmail')
            >>> print(info['name'])
            'Google Workspace Gmail'
        """
        if not system_type or not isinstance(system_type, str):
            raise ValueError("System type must be a non-empty string")

        normalized_type = system_type.lower().strip()
        logger.info(f"Retrieving system information for: {normalized_type}")

        if normalized_type == EmailSystemType.GMAIL.value:
            return {
                "name": "Google Workspace Gmail",
                "description": "Gmail integration using Google Workspace Gmail API with OAuth 2.0 authentication",
                "authentication": "OAuth 2.0 with Google Identity Platform",
                "capabilities": [
                    "Email reading and sending",
                    "Label management",
                    "search queries",
                    "Attachment handling",
                    "Contact integration",
                ],
                "requirements": [
                    "Google Cloud Project with Gmail API enabled",
                    "OAuth 2.0 Client ID credentials",
                    "Google Workspace account or Gmail account",
                ],
                "documentation": "https://developers.google.com/workspace/gmail/api/guides",
            }

        elif normalized_type in [
            EmailSystemType.MICROSOFT_GRAPH.value,
            EmailSystemType.OUTLOOK.value,
            EmailSystemType.OFFICE365.value,
        ]:
            return {
                "name": "Microsoft Graph (Office 365)",
                "description": "Microsoft Graph API integration for Office 365/Exchange Online with Azure AD authentication",
                "authentication": "OAuth 2.0 with Microsoft Identity Platform (Azure AD)",
                "capabilities": [
                    "Email reading and sending",
                    "Folder management",
                    "search and filtering",
                    "Attachment handling",
                    "Calendar integration potential",
                    "User profile access",
                ],
                "requirements": [
                    "Azure AD app registration",
                    "Appropriate Microsoft Graph permissions",
                    "Office 365 or Microsoft 365 account",
                ],
                "documentation": "https://docs.microsoft.com/en-us/graph/api/resources/mail-api-overview",
            }

        else:
            supported_types = cls.get_supported_types()
            logger.error(f"Unsupported system type for info: {normalized_type}")
            raise EmailSystemError(
                f"Unsupported email system type: '{system_type}'. "
                f"Supported types: {supported_types}"
            )
