"""
Credential Manager - Centralized credential handling

Following architecture decisions: Centralized, secure credential management
with validation, rotation, and proper error handling.
"""

import os
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CredentialError(Exception):
    """Custom exception for credential operations"""
    pass


class Credential(BaseModel):
    """Secure credential storage model"""
    name: str
    value: str
    encrypted: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_validated: Optional[datetime] = None
    validation_status: str = "unknown"  # unknown, valid, invalid, expired


class CredentialManager:
    """
    Centralized credential management system
    
    Handles secure storage, validation, and rotation of API keys and secrets.
    Never logs sensitive data, provides audit trails for access.
    """
    
    def __init__(self, credentials_file: str = ".credentials.json"):
        self.credentials_file = Path(credentials_file)
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        self._credentials: Dict[str, Credential] = {}
        self._load_credentials()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for credential storage"""
        key_file = Path(".credential_key")
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)  # Restrict permissions
            return key
    
    def _load_credentials(self) -> None:
        """Load credentials from encrypted storage"""
        if not self.credentials_file.exists():
            return
        
        try:
            with open(self.credentials_file, 'r') as f:
                encrypted_data = json.load(f)
            
            for name, data in encrypted_data.items():
                if data.get('encrypted', True):
                    # Decrypt the value
                    decrypted_value = self.fernet.decrypt(data['value'].encode()).decode()
                    data['value'] = decrypted_value
                
                self._credentials[name] = Credential(**data)
                
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise CredentialError(f"Failed to load credentials: {e}")
    
    def _save_credentials(self) -> None:
        """Save credentials to encrypted storage"""
        try:
            encrypted_data = {}
            
            for name, credential in self._credentials.items():
                data = credential.dict()
                
                if credential.encrypted:
                    # Encrypt the value before saving
                    encrypted_value = self.fernet.encrypt(credential.value.encode()).decode()
                    data['value'] = encrypted_value
                
                encrypted_data[name] = data
            
            with open(self.credentials_file, 'w') as f:
                json.dump(encrypted_data, f, indent=2, default=str)
            
            # Restrict file permissions
            self.credentials_file.chmod(0o600)
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise CredentialError(f"Failed to save credentials: {e}")
    
    def store_credential(self, name: str, value: str, 
                        expires_at: Optional[datetime] = None,
                        encrypt: bool = True) -> None:
        """
        Store a credential securely
        
        Args:
            name: Credential identifier
            value: Credential value (API key, token, etc.)
            expires_at: Optional expiration date
            encrypt: Whether to encrypt the value
        """
        try:
            credential = Credential(
                name=name,
                value=value,
                encrypted=encrypt,
                expires_at=expires_at
            )
            
            self._credentials[name] = credential
            self._save_credentials()
            
            logger.info(f"Stored credential: {name}")
            
        except Exception as e:
            logger.error(f"Failed to store credential {name}: {e}")
            raise CredentialError(f"Failed to store credential: {e}")
    
    def get_credential(self, name: str) -> Optional[str]:
        """
        Get a credential value
        
        Args:
            name: Credential identifier
            
        Returns:
            Credential value or None if not found
        """
        try:
            credential = self._credentials.get(name)
            if not credential:
                # Try environment variable as fallback
                env_value = os.getenv(name)
                if env_value:
                    logger.info(f"Retrieved credential {name} from environment")
                    return env_value
                return None
            
            # Check if expired
            if credential.expires_at and credential.expires_at < datetime.now():
                logger.warning(f"Credential {name} has expired")
                return None
            
            logger.info(f"Retrieved credential: {name}")
            return credential.value
            
        except Exception as e:
            logger.error(f"Failed to get credential {name}: {e}")
            return None
    
    def validate_credential(self, name: str, validator_func: callable) -> bool:
        """
        Validate a credential using a custom validator function
        
        Args:
            name: Credential identifier
            validator_func: Function that takes credential value and returns bool
            
        Returns:
            True if valid, False otherwise
        """
        try:
            credential = self._credentials.get(name)
            if not credential:
                return False
            
            is_valid = validator_func(credential.value)
            
            # Update validation status
            credential.last_validated = datetime.now()
            credential.validation_status = "valid" if is_valid else "invalid"
            self._save_credentials()
            
            logger.info(f"Validated credential {name}: {'valid' if is_valid else 'invalid'}")
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to validate credential {name}: {e}")
            return False
    
    def list_credentials(self) -> Dict[str, Dict[str, Any]]:
        """
        List all stored credentials (without values)
        
        Returns:
            Dictionary of credential metadata
        """
        result = {}
        
        for name, credential in self._credentials.items():
            result[name] = {
                "name": credential.name,
                "encrypted": credential.encrypted,
                "expires_at": credential.expires_at,
                "created_at": credential.created_at,
                "last_validated": credential.last_validated,
                "validation_status": credential.validation_status,
                "is_expired": credential.expires_at and credential.expires_at < datetime.now()
            }
        
        return result
    
    def delete_credential(self, name: str) -> bool:
        """
        Delete a stored credential
        
        Args:
            name: Credential identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            if name in self._credentials:
                del self._credentials[name]
                self._save_credentials()
                logger.info(f"Deleted credential: {name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete credential {name}: {e}")
            return False
    
    def rotate_credential(self, name: str, new_value: str) -> bool:
        """
        Rotate a credential to a new value
        
        Args:
            name: Credential identifier
            new_value: New credential value
            
        Returns:
            True if rotated successfully
        """
        try:
            credential = self._credentials.get(name)
            if not credential:
                return False
            
            # Update with new value
            credential.value = new_value
            credential.created_at = datetime.now()
            credential.validation_status = "unknown"
            credential.last_validated = None
            
            self._save_credentials()
            logger.info(f"Rotated credential: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate credential {name}: {e}")
            return False
    
    def get_expiring_credentials(self, days: int = 7) -> Dict[str, Credential]:
        """
        Get credentials expiring within specified days
        
        Args:
            days: Number of days to check ahead
            
        Returns:
            Dictionary of expiring credentials
        """
        expiring = {}
        cutoff_date = datetime.now() + timedelta(days=days)
        
        for name, credential in self._credentials.items():
            if credential.expires_at and credential.expires_at <= cutoff_date:
                expiring[name] = credential
        
        return expiring
    
    def validate_all_credentials(self, validators: Dict[str, callable]) -> Dict[str, bool]:
        """
        Validate all credentials using provided validators
        
        Args:
            validators: Dictionary mapping credential names to validator functions
            
        Returns:
            Dictionary of validation results
        """
        results = {}
        
        for name, validator in validators.items():
            if name in self._credentials:
                results[name] = self.validate_credential(name, validator)
            else:
                results[name] = False
        
        return results


# Global credential manager instance
_credential_manager: Optional[CredentialManager] = None


def get_credential_manager() -> CredentialManager:
    """Get the global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager


# Convenience functions for credential storage
def store_openai_key(key: str, expires_days: Optional[int] = None) -> None:
    """Store OpenAI API key with optional expiration"""
    cm = get_credential_manager()
    expires_at = None
    if expires_days:
        expires_at = datetime.now() + timedelta(days=expires_days)
    
    cm.store_credential("OPENAI_API_KEY", key, expires_at)


def store_anthropic_key(key: str, expires_days: Optional[int] = None) -> None:
    """Store Anthropic API key with optional expiration"""
    cm = get_credential_manager()
    expires_at = None
    if expires_days:
        expires_at = datetime.now() + timedelta(days=expires_days)
    
    cm.store_credential("ANTHROPIC_API_KEY", key, expires_at)


def store_supabase_credentials(url: str, key: str) -> None:
    """Store Supabase credentials"""
    cm = get_credential_manager()
    cm.store_credential("SUPABASE_URL", url)
    cm.store_credential("SUPABASE_KEY", key)


# Credential validators
def validate_openai_key(api_key: str) -> bool:
    """Validate OpenAI API key format"""
    return api_key.startswith("sk-") and len(api_key) > 20


def validate_anthropic_key(api_key: str) -> bool:
    """Validate Anthropic API key format"""
    return api_key.startswith("sk-ant-") and len(api_key) > 20


def validate_google_key(api_key: str) -> bool:
    """Validate Google API key format"""
    return len(api_key) > 20 and not api_key.startswith("sk-")


# Default validators mapping
DEFAULT_VALIDATORS = {
    "OPENAI_API_KEY": validate_openai_key,
    "ANTHROPIC_API_KEY": validate_anthropic_key,
    "GOOGLE_API_KEY": validate_google_key
}