"""
User MongoDB model
"""
from typing import Optional, List
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from datetime import datetime

from src.domain.entities.user import UserRole


class User(Document):
    """User document model for MongoDB"""
    
    email: Indexed(EmailStr, unique=True)
    hashed_password: str
    
    # Profile
    full_name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Role and permissions
    role: UserRole = UserRole.USER
    tenant_ids: List[str] = Field(default_factory=list)
    
    # Status
    is_active: bool = True
    is_verified: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    
    class Settings:
        name = "users"
        indexes = [
            "email",
            "role",
            "tenant_ids",
        ]


