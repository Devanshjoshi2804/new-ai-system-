"""
Dynamic AI Agent Factory
Creates partner-specific AI agents that can autonomously execute APIs
"""
import logging
from typing import List, Dict, Any, Optional
# from langchain_openai import ChatOpenAI  # Disabled - no OpenAI API key
from crewai import Agent, Task, Crew, Process
from langchain_core.tools import BaseTool

from src.domain.value_objects.api_schema import APISpecification
from src.application.ai.understanding.workflow_analyzer import BusinessWorkflow
from src.application.ai.generators.tool_generator import ToolGenerator
from src.application.ai.generators.adapter_generator import DynamicAdapterGenerator
from src.infrastructure.ai.providers import get_ai_provider

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating partner-specific AI agents
    
    Each partner gets custom agents that understand their API
    and can execute operations autonomously
    """
    
    def __init__(self):
        self.tool_generator = ToolGenerator()
        self.adapter_generator = DynamicAdapterGenerator()
        # self.llm = ChatOpenAI(model="gpt-4", temperature=0.7)  # Disabled - no OpenAI API key
        # Using best available AI provider (Groq > Gemini > Mistral)
        self.ai_provider = get_ai_provider()  # Auto-selects best provider
        self.llm = None  # CrewAI agents will use AI provider through custom integration
    
    async def create_booking_agent(
        self,
        partner_id: str,
        api_spec: APISpecification,
        workflows: List[BusinessWorkflow],
        api_credentials: Optional[Dict[str, str]] = None
    ) -> Agent:
        """
        Create an agent specialized in booking operations
        
        Args:
            partner_id: Partner identifier
            api_spec: API specification
            workflows: Business workflows (especially booking flow)
            api_credentials: API authentication credentials
            
        Returns:
            CrewAI Agent configured for bookings
        """
        try:
            logger.info(f"Creating booking agent for partner: {partner_id}")
            
            # Find booking workflow
            booking_workflow = self._find_workflow(workflows, ["booking", "order", "create", "shipment"])
            
            if not booking_workflow:
                logger.warning(f"No booking workflow found for {partner_id}")
                booking_workflow = BusinessWorkflow(
                    name="Generic Booking",
                    description="Create bookings using available endpoints",
                    endpoint_sequence=[],
                    required_fields={},
                    optional_fields={},
                    business_rules=[],
                    error_handling={},
                    prerequisites=[]
                )
            
            # Generate adapter code
            adapter_code = await self.adapter_generator.generate_adapter(
                partner_id=partner_id,
                api_spec=api_spec
            )
            
            adapter_class_name = self.adapter_generator._generate_class_name(partner_id)
            
            # Get booking-related endpoints
            booking_endpoints = self._get_booking_endpoints(api_spec, booking_workflow)
            
            # Generate tools from endpoints
            tools = await self.tool_generator.generate_tools_from_workflow(
                workflow_endpoints=booking_endpoints,
                adapter_code=adapter_code,
                adapter_class_name=adapter_class_name,
                partner_id=partner_id,
                api_credentials=api_credentials
            )
            
            # Create agent (Note: llm parameter removed - using Gemini instead of OpenAI)
            agent = Agent(
                role=f"{partner_id} Booking Specialist",
                goal=f"Create and manage shipment bookings using {partner_id}'s API",
                backstory=f"""You are an expert in {partner_id}'s logistics API.
                You understand the booking workflow: {booking_workflow.description}
                
                Required steps: {', '.join(booking_workflow.endpoint_sequence)}
                Business rules: {', '.join(booking_workflow.business_rules)}
                
                You can autonomously call the API endpoints to create bookings, 
                validate addresses, calculate rates, and handle any booking-related operations.
                
                Always follow the correct sequence of API calls and handle errors gracefully.""",
                tools=tools,
                # llm=self.llm,  # Disabled - no OpenAI API key
                verbose=True,
                allow_delegation=False
            )
            
            logger.info(f"Booking agent created with {len(tools)} tools")
            return agent
        
        except Exception as e:
            logger.error(f"Error creating booking agent: {e}")
            raise
    
    async def create_tracking_agent(
        self,
        partner_id: str,
        api_spec: APISpecification,
        workflows: List[BusinessWorkflow],
        api_credentials: Optional[Dict[str, str]] = None
    ) -> Agent:
        """
        Create an agent specialized in tracking operations
        """
        try:
            logger.info(f"Creating tracking agent for partner: {partner_id}")
            
            # Find tracking workflow
            tracking_workflow = self._find_workflow(workflows, ["track", "status", "shipment"])
            
            # Generate tools for tracking endpoints
            adapter_code = await self.adapter_generator.generate_adapter(
                partner_id=partner_id,
                api_spec=api_spec
            )
            
            adapter_class_name = self.adapter_generator._generate_class_name(partner_id)
            
            tracking_endpoints = self._get_tracking_endpoints(api_spec)
            
            tools = await self.tool_generator.generate_tools_from_workflow(
                workflow_endpoints=tracking_endpoints,
                adapter_code=adapter_code,
                adapter_class_name=adapter_class_name,
                partner_id=partner_id,
                api_credentials=api_credentials
            )
            
            # Create agent (Note: llm parameter removed - using Gemini instead of OpenAI)
            agent = Agent(
                role=f"{partner_id} Tracking Specialist",
                goal=f"Track shipments and provide status updates using {partner_id}'s API",
                backstory=f"""You are an expert in tracking shipments with {partner_id}.
                You can check shipment status, get delivery updates, and provide tracking information.
                
                You understand the tracking workflow and can handle various tracking identifiers 
                (AWB numbers, order IDs, etc.).""",
                tools=tools,
                # llm=self.llm,  # Disabled - no OpenAI API key
                verbose=True,
                allow_delegation=False
            )
            
            logger.info(f"Tracking agent created with {len(tools)} tools")
            return agent
        
        except Exception as e:
            logger.error(f"Error creating tracking agent: {e}")
            raise
    
    async def create_agent_crew(
        self,
        partner_id: str,
        api_spec: APISpecification,
        workflows: List[BusinessWorkflow],
        api_credentials: Optional[Dict[str, str]] = None
    ) -> Crew:
        """
        Create a complete crew of agents for a partner
        
        Returns:
            CrewAI Crew with multiple specialized agents
        """
        try:
            logger.info(f"Creating agent crew for partner: {partner_id}")
            
            # Create specialized agents
            booking_agent = await self.create_booking_agent(
                partner_id, api_spec, workflows, api_credentials
            )
            
            tracking_agent = await self.create_tracking_agent(
                partner_id, api_spec, workflows, api_credentials
            )
            
            # Create crew
            crew = Crew(
                agents=[booking_agent, tracking_agent],
                tasks=[],  # Tasks will be added dynamically
                process=Process.sequential,
                verbose=True
            )
            
            logger.info(f"Agent crew created for {partner_id}")
            return crew
        
        except Exception as e:
            logger.error(f"Error creating agent crew: {e}")
            raise
    
    def _find_workflow(
        self,
        workflows: List[BusinessWorkflow],
        keywords: List[str]
    ) -> Optional[BusinessWorkflow]:
        """Find workflow matching keywords"""
        for workflow in workflows:
            if any(keyword.lower() in workflow.name.lower() for keyword in keywords):
                return workflow
        return None
    
    def _get_booking_endpoints(
        self,
        api_spec: APISpecification,
        booking_workflow: BusinessWorkflow
    ) -> List:
        """Get endpoints related to booking"""
        from domain.value_objects.api_endpoint import APIEndpoint
        
        # If workflow has specific endpoints, use those
        if booking_workflow.endpoint_sequence:
            endpoint_paths = [
                ep.split(' ')[1] if ' ' in ep else ep
                for ep in booking_workflow.endpoint_sequence
            ]
            return [
                ep for ep in api_spec.endpoints
                if ep.path in endpoint_paths
            ]
        
        # Otherwise, find booking-related endpoints
        booking_keywords = ['book', 'order', 'create', 'shipment', 'rate', 'validate', 'pincode']
        return [
            ep for ep in api_spec.endpoints
            if any(kw in ep.path.lower() or (ep.summary and kw in ep.summary.lower())
                   for kw in booking_keywords)
        ]
    
    def _get_tracking_endpoints(self, api_spec: APISpecification) -> List:
        """Get endpoints related to tracking"""
        tracking_keywords = ['track', 'status', 'shipment', 'awb']
        return [
            ep for ep in api_spec.endpoints
            if ep.method.value == 'GET' and any(
                kw in ep.path.lower() or (ep.summary and kw in ep.summary.lower())
                for kw in tracking_keywords
            )
        ]


class AgentRegistry:
    """
    Registry for storing and retrieving partner agents
    """
    
    def __init__(self):
        self._agents: Dict[str, Dict[str, Agent]] = {}
        self._crews: Dict[str, Crew] = {}
    
    def register_agent(self, partner_id: str, agent_type: str, agent: Agent):
        """Register an agent"""
        if partner_id not in self._agents:
            self._agents[partner_id] = {}
        self._agents[partner_id][agent_type] = agent
        logger.info(f"Registered {agent_type} agent for {partner_id}")
    
    def get_agent(self, partner_id: str, agent_type: str) -> Optional[Agent]:
        """Get a registered agent"""
        return self._agents.get(partner_id, {}).get(agent_type)
    
    def register_crew(self, partner_id: str, crew: Crew):
        """Register a crew"""
        self._crews[partner_id] = crew
        logger.info(f"Registered crew for {partner_id}")
    
    def get_crew(self, partner_id: str) -> Optional[Crew]:
        """Get a registered crew"""
        return self._crews.get(partner_id)
    
    def has_agents(self, partner_id: str) -> bool:
        """Check if partner has registered agents"""
        return partner_id in self._agents or partner_id in self._crews


# Global registry
_agent_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """Get global agent registry"""
    return _agent_registry


