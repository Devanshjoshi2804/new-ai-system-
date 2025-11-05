"""
Integration Configuration MongoDB model
"""
from typing import Optional, Dict, Any, List
from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime

from src.domain.entities.integration_config import IntegrationStatus


class IntegrationConfig(Document):
    """Integration Configuration document model for MongoDB"""
    
    partner_id: Indexed(str)
    tenant_id: Indexed(str)
    documentation_id: Indexed(str)
    
    # API Specification
    api_spec: Dict[str, Any]
    
    # Generated code
    adapter_code: Optional[str] = None
    adapter_file_path: Optional[str] = None
    schema_code: Optional[str] = None
    
    # Generated tools and agents
    generated_tools: List[Dict[str, Any]] = Field(default_factory=list)
    generated_agents: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Business workflows
    workflows: Dict[str, Any] = Field(default_factory=dict)
    
    # Validation
    validation_status: IntegrationStatus = IntegrationStatus.GENERATING
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    
    # Testing
    test_results: Optional[Dict[str, Any]] = None
    test_passed: bool = False
    
    # Runtime information
    is_deployed: bool = False
    deployment_version: int = 1
    
    # Performance metrics
    average_response_time: Optional[float] = None
    success_rate: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    validated_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    
    class Settings:
        name = "integration_configurations"
        indexes = [
            "partner_id",
            "tenant_id",
            "validation_status",
            "is_deployed",
        ]


