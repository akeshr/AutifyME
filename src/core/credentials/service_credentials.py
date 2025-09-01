"""
Service Provider Credentials

Clean, simple credential classes for each service provider.
Each service knows how to configure itself from the credential manager.
"""

from typing import Optional, Dict, Any, Union
from pydantic import BaseModel
from supabase import create_client, Client
from .credential_manager import get_credential_manager


# ==================== DATABASE SERVICES ====================

class Supabase(BaseModel):
    """Supabase service credentials"""
    url: str
    key: str
    
    def create_client(self) -> Client:
        """Create Supabase client"""
        return create_client(self.url, self.key)
    
    @classmethod
    def load(cls) -> "Supabase":
        """Load Supabase credentials from credential manager"""
        cm = get_credential_manager()
        url = cm.get_credential("SUPABASE_URL")
        key = cm.get_credential("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Supabase credentials not found. Please configure SUPABASE_URL and SUPABASE_KEY")
        
        return cls(url=url, key=key)


class PostgreSQL(BaseModel):
    """PostgreSQL service credentials"""
    host: str
    port: int = 5432
    database: str
    username: str
    password: str
    
    @classmethod
    def load(cls) -> "PostgreSQL":
        """Load PostgreSQL credentials from credential manager"""
        cm = get_credential_manager()
        host = cm.get_credential("POSTGRES_HOST")
        database = cm.get_credential("POSTGRES_DATABASE")
        username = cm.get_credential("POSTGRES_USERNAME")
        password = cm.get_credential("POSTGRES_PASSWORD")
        port = int(cm.get_credential("POSTGRES_PORT") or "5432")
        
        if not all([host, database, username, password]):
            raise ValueError("PostgreSQL credentials incomplete")
        
        return cls(host=host, port=port, database=database, username=username, password=password)
    
    def connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class MongoDB(BaseModel):
    """MongoDB service credentials"""
    connection_string: str
    database: str
    
    @classmethod
    def load(cls) -> "MongoDB":
        """Load MongoDB credentials from credential manager"""
        cm = get_credential_manager()
        connection_string = cm.get_credential("MONGODB_CONNECTION_STRING")
        database = cm.get_credential("MONGODB_DATABASE")
        
        if not connection_string or not database:
            raise ValueError("MongoDB credentials not found")
        
        return cls(connection_string=connection_string, database=database)


# ==================== AI SERVICES ====================

class OpenAI(BaseModel):
    """OpenAI service credentials"""
    api_key: str
    organization_id: Optional[str] = None
    
    @classmethod
    def load(cls) -> "OpenAI":
        """Load OpenAI credentials from credential manager"""
        cm = get_credential_manager()
        api_key = cm.get_credential("OPENAI_API_KEY")
        organization_id = cm.get_credential("OPENAI_ORGANIZATION_ID")
        
        if not api_key:
            raise ValueError("OpenAI API key not found")
        
        return cls(api_key=api_key, organization_id=organization_id)


class Anthropic(BaseModel):
    """Anthropic service credentials"""
    api_key: str
    
    @classmethod
    def load(cls) -> "Anthropic":
        """Load Anthropic credentials from credential manager"""
        cm = get_credential_manager()
        api_key = cm.get_credential("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError("Anthropic API key not found")
        
        return cls(api_key=api_key)


class Google(BaseModel):
    """Google service credentials"""
    api_key: str
    project_id: Optional[str] = None
    
    @classmethod
    def load(cls) -> "Google":
        """Load Google credentials from credential manager"""
        cm = get_credential_manager()
        api_key = cm.get_credential("GOOGLE_API_KEY")
        project_id = cm.get_credential("GOOGLE_PROJECT_ID")
        
        if not api_key:
            raise ValueError("Google API key not found")
        
        return cls(api_key=api_key, project_id=project_id)


# ==================== STORAGE SERVICES ====================

class GoogleDrive(BaseModel):
    """Google Drive service credentials"""
    credentials_path: str
    folder_id: Optional[str] = None
    
    @classmethod
    def load(cls) -> "GoogleDrive":
        """Load Google Drive credentials from credential manager"""
        cm = get_credential_manager()
        credentials_path = cm.get_credential("GOOGLE_DRIVE_CREDENTIALS_PATH")
        folder_id = cm.get_credential("GOOGLE_DRIVE_FOLDER_ID")
        
        if not credentials_path:
            raise ValueError("Google Drive credentials not found")
        
        return cls(credentials_path=credentials_path, folder_id=folder_id)


class AWS(BaseModel):
    """AWS service credentials"""
    access_key_id: str
    secret_access_key: str
    region: str = "us-east-1"
    
    @classmethod
    def load(cls) -> "AWS":
        """Load AWS credentials from credential manager"""
        cm = get_credential_manager()
        access_key_id = cm.get_credential("AWS_ACCESS_KEY_ID")
        secret_access_key = cm.get_credential("AWS_SECRET_ACCESS_KEY")
        region = cm.get_credential("AWS_REGION") or "us-east-1"
        
        if not access_key_id or not secret_access_key:
            raise ValueError("AWS credentials not found")
        
        return cls(access_key_id=access_key_id, secret_access_key=secret_access_key, region=region)


# ==================== CACHED INSTANCES ====================

# Database services
_supabase: Optional[Supabase] = None
_postgresql: Optional[PostgreSQL] = None
_mongodb: Optional[MongoDB] = None

# AI services
_openai: Optional[OpenAI] = None
_anthropic: Optional[Anthropic] = None
_google: Optional[Google] = None

# Storage services
_google_drive: Optional[GoogleDrive] = None
_aws: Optional[AWS] = None


# ==================== SERVICE GETTERS ====================

def supabase() -> Supabase:
    """Get Supabase service - cached after first call"""
    global _supabase
    if _supabase is None:
        _supabase = Supabase.load()
    return _supabase


def postgresql() -> PostgreSQL:
    """Get PostgreSQL service - cached after first call"""
    global _postgresql
    if _postgresql is None:
        _postgresql = PostgreSQL.load()
    return _postgresql


def mongodb() -> MongoDB:
    """Get MongoDB service - cached after first call"""
    global _mongodb
    if _mongodb is None:
        _mongodb = MongoDB.load()
    return _mongodb


def openai() -> OpenAI:
    """Get OpenAI service - cached after first call"""
    global _openai
    if _openai is None:
        _openai = OpenAI.load()
    return _openai


def anthropic() -> Anthropic:
    """Get Anthropic service - cached after first call"""
    global _anthropic
    if _anthropic is None:
        _anthropic = Anthropic.load()
    return _anthropic


def google() -> Google:
    """Get Google service - cached after first call"""
    global _google
    if _google is None:
        _google = Google.load()
    return _google


def google_drive() -> GoogleDrive:
    """Get Google Drive service - cached after first call"""
    global _google_drive
    if _google_drive is None:
        _google_drive = GoogleDrive.load()
    return _google_drive


def aws() -> AWS:
    """Get AWS service - cached after first call"""
    global _aws
    if _aws is None:
        _aws = AWS.load()
    return _aws


def refresh_all():
    """Refresh all cached service credentials"""
    global _supabase, _postgresql, _mongodb
    global _openai, _anthropic, _google
    global _google_drive, _aws
    
    # Reset all cached services
    _supabase = None
    _postgresql = None
    _mongodb = None
    _openai = None
    _anthropic = None
    _google = None
    _google_drive = None
    _aws = None


# ==================== TYPE ALIASES ====================

# Generic types for tools that can work with any database
DatabaseService = Union[Supabase, PostgreSQL, MongoDB]
AIService = Union[OpenAI, Anthropic, Google]
StorageService = Union[GoogleDrive, AWS]