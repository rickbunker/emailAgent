"""
Email interface factory for creating email system implementations.

This module provides a factory class to easily instantiate different
email system implementations based on configuration.
"""

from typing import Dict, Any, Optional, List
from enum import Enum

from .base import BaseEmailInterface, EmailSystemError
from .gmail import GmailInterface
from .msgraph import MicrosoftGraphInterface

class EmailSystemType(Enum):
    """Supported email system types."""
    GMAIL = "gmail"
    MICROSOFT_GRAPH = "microsoft_graph"
    OUTLOOK = "outlook"  # Alias for Microsoft Graph
    OFFICE365 = "office365"  # Alias for Microsoft Graph

class EmailInterfaceFactory:
    """Factory for creating email interface instances."""
    
    @classmethod
    def create(cls, system_type: str, **kwargs) -> BaseEmailInterface:
        """
        Create an email interface instance.
        
        Args:
            system_type: Type of email system ('gmail', 'microsoft_graph', 'outlook', 'office365')
            **kwargs: Additional arguments passed to the interface constructor
            
        Returns:
            BaseEmailInterface: Configured email interface instance
            
        Raises:
            EmailSystemError: If unsupported system type or creation fails
        """
        try:
            system_type = system_type.lower().strip()
            
            if system_type == EmailSystemType.GMAIL.value:
                return GmailInterface(**kwargs)
            
            elif system_type in [
                EmailSystemType.MICROSOFT_GRAPH.value,
                EmailSystemType.OUTLOOK.value,
                EmailSystemType.OFFICE365.value
            ]:
                return MicrosoftGraphInterface(**kwargs)
            
            else:
                raise EmailSystemError(f"Unsupported email system type: {system_type}")
                
        except Exception as e:
            if isinstance(e, EmailSystemError):
                raise
            raise EmailSystemError(f"Failed to create email interface: {e}")
    
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> BaseEmailInterface:
        """
        Create an email interface from configuration dictionary.
        
        Args:
            config: Configuration dictionary containing:
                - 'type': Email system type
                - 'credentials': Authentication credentials
                - Other system-specific settings
                
        Returns:
            BaseEmailInterface: Configured email interface instance
            
        Example:
            config = {
                'type': 'gmail',
                'credentials': {
                    'credentials_file': 'path/to/credentials.json',
                    'token_file': 'path/to/token.json'
                }
            }
            interface = EmailInterfaceFactory.create_from_config(config)
        """
        if 'type' not in config:
            raise EmailSystemError("Configuration must specify 'type' field")
        
        system_type = config['type']
        
        # Extract credentials and other settings
        settings = config.copy()
        settings.pop('type')
        
        return cls.create(system_type, **settings)
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """Get list of supported email system types."""
        return [system_type.value for system_type in EmailSystemType]
    
    @classmethod
    def get_credentials_template(cls, system_type: str) -> Dict[str, Any]:
        """
        Get a template for credentials configuration for a given system type.
        
        Args:
            system_type: Email system type
            
        Returns:
            Dict containing credential field templates with descriptions
        """
        system_type = system_type.lower().strip()
        
        if system_type == EmailSystemType.GMAIL.value:
            return {
                'credentials_file': {
                    'description': 'Path to Google OAuth2 credentials.json file (for first-time auth)',
                    'required': True,
                    'example': '/path/to/credentials.json'
                },
                'token_file': {
                    'description': 'Path to save/load OAuth2 token (optional)',
                    'required': False,
                    'example': '/path/to/token.json'
                },
                'token_data': {
                    'description': 'Direct token data dict (alternative to token_file)',
                    'required': False,
                    'example': {'access_token': '...', 'refresh_token': '...'}
                }
            }
        
        elif system_type in [
            EmailSystemType.MICROSOFT_GRAPH.value,
            EmailSystemType.OUTLOOK.value,
            EmailSystemType.OFFICE365.value
        ]:
            return {
                'client_id': {
                    'description': 'Azure AD Application (client) ID',
                    'required': True,
                    'example': '12345678-1234-1234-1234-123456789012'
                },
                'client_secret': {
                    'description': 'Azure AD Client secret (optional for public clients)',
                    'required': False,
                    'example': 'your-client-secret'
                },
                'tenant_id': {
                    'description': 'Azure AD Directory (tenant) ID',
                    'required': False,
                    'default': 'common',
                    'example': '87654321-4321-4321-4321-210987654321'
                },
                'redirect_uri': {
                    'description': 'OAuth2 redirect URI',
                    'required': False,
                    'default': 'http://localhost:8080',
                    'example': 'http://localhost:8080'
                }
            }
        
        else:
            raise EmailSystemError(f"Unsupported email system type: {system_type}") 