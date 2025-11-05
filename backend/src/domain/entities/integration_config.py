"""
Integration Configuration domain entity
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class IntegrationStatus(str, Enum):
    """Integration configuration status"""
    GENERATING = "generating"
    GENERATED = "generated"
    VALIDATING = "validating"
    VALIDATED = "validated"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class IntegrationConfig(BaseModel):
    """Integration Configuration entity - Generated from documentation"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    partner_id: str
    tenant_id: str
    documentation_id: str
    
    # API Specification
    api_spec: Dict[str, Any]  # APISpecification as dict
    
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "partner_id": "uuid-here",
                "tenant_id": "tenant-uuid",
                "documentation_id": "doc-uuid",
                "api_spec": {"title": "Partner API", "version": "1.0.0"}
            }
        }
    
    def update_status(self, status: IntegrationStatus):
        """Update integration status"""
        self.validation_status = status
        self.updated_at = datetime.utcnow()
        
        if status == IntegrationStatus.VALIDATED:
            self.validated_at = datetime.utcnow()
        elif status == IntegrationStatus.ACTIVE:
            self.is_deployed = True
            self.deployed_at = datetime.utcnow()
    
    def add_validation_error(self, error: str):
        """Add validation error"""
        self.validation_errors.append(error)
        self.validation_status = IntegrationStatus.FAILED
    
    def add_validation_warning(self, warning: str):
        """Add validation warning"""
        self.validation_warnings.append(warning)
    
    def set_adapter_code(self, code: str, file_path: str):
        """Set generated adapter code"""
        self.adapter_code = code
        self.adapter_file_path = file_path
        self.updated_at = datetime.utcnow()
    
    def add_generated_tool(self, tool_info: Dict[str, Any]):
        """Add generated tool information"""
        self.generated_tools.append(tool_info)
    
    def add_generated_agent(self, agent_info: Dict[str, Any]):
        """Add generated agent information"""
        self.generated_agents.append(agent_info)
    
    def is_ready_for_deployment(self) -> bool:
        """Check if integration is ready for deployment"""
        return (
            self.validation_status == IntegrationStatus.VALIDATED
            and len(self.validation_errors) == 0
            and self.adapter_code is not None
            and len(self.generated_agents) > 0
        )
    
    def deploy(self):
        """Mark integration as deployed"""
        if not self.is_ready_for_deployment():
            raise ValueError("Integration not ready for deployment")
        
        self.is_deployed = True
        self.validation_status = IntegrationStatus.ACTIVE
        self.deployed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


