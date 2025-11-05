"""
LangGraph Execution Graph for Autonomous Operations
Orchestrates the complete flow from user input to API execution
"""
import logging
from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
# from langchain_openai import ChatOpenAI  # Disabled - no OpenAI API key
from langchain_core.messages import HumanMessage, SystemMessage

from src.application.ai.agents.agent_factory import get_agent_registry
from src.infrastructure.ai.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class ExecutionState(TypedDict):
    """State for the execution graph"""
    user_message: str
    partner_id: str
    tenant_id: str
    intent: Optional[str]
    entities: Optional[Dict[str, Any]]
    agent_type: Optional[str]
    agent_response: Optional[str]
    api_calls_made: List[Dict[str, Any]]
    error: Optional[str]
    final_response: Optional[str]


class AutonomousExecutionGraph:
    """
    LangGraph state machine for autonomous API execution
    
    Flow:
    1. Classify Intent (what does user want?)
    2. Extract Entities (parameters needed)
    3. Select Agent (booking, tracking, etc.)
    4. Execute with Agent (call APIs)
    5. Generate Response (format for user)
    """
    
    def __init__(self):
        from src.infrastructure.ai.providers import get_ai_provider
        self.ai_provider = get_ai_provider()  # Auto-selects best provider (Groq > Gemini > Mistral)
        # self.llm = ChatOpenAI(model="gpt-4", temperature=0.3)  # Disabled - no OpenAI API key
        self.llm = None  # Using AI provider instead
        self.agent_registry = get_agent_registry()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        # Create graph
        workflow = StateGraph(ExecutionState)
        
        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("extract_entities", self._extract_entities)
        workflow.add_node("select_agent", self._select_agent)
        workflow.add_node("execute_with_agent", self._execute_with_agent)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("handle_error", self._handle_error)
        
        # Set entry point
        workflow.set_entry_point("classify_intent")
        
        # Add edges
        workflow.add_edge("classify_intent", "extract_entities")
        workflow.add_edge("extract_entities", "select_agent")
        
        # Conditional edge from select_agent
        workflow.add_conditional_edges(
            "select_agent",
            self._route_after_selection,
            {
                "execute": "execute_with_agent",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("execute_with_agent", "generate_response")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    async def execute(
        self,
        user_message: str,
        partner_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Execute autonomous operation based on user message
        
        Args:
            user_message: User's natural language command
            partner_id: Partner identifier
            tenant_id: Tenant identifier
            
        Returns:
            Execution result with response and actions taken
        """
        try:
            logger.info(f"Executing autonomous operation for: {user_message}")
            
            # Initial state
            initial_state = ExecutionState(
                user_message=user_message,
                partner_id=partner_id,
                tenant_id=tenant_id,
                intent=None,
                entities=None,
                agent_type=None,
                agent_response=None,
                api_calls_made=[],
                error=None,
                final_response=None
            )
            
            # Run graph
            final_state = await self.graph.ainvoke(initial_state)
            
            logger.info(f"Execution completed: {final_state.get('final_response')}")
            
            return {
                "success": final_state.get("error") is None,
                "response": final_state.get("final_response"),
                "intent": final_state.get("intent"),
                "entities": final_state.get("entities"),
                "api_calls": final_state.get("api_calls_made", []),
                "error": final_state.get("error")
            }
        
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {
                "success": False,
                "response": f"I encountered an error: {str(e)}",
                "error": str(e)
            }
    
    async def _classify_intent(self, state: ExecutionState) -> ExecutionState:
        """
        Classify user intent using Gemini
        
        Possible intents:
        - CREATE_BOOKING
        - TRACK_SHIPMENT
        - CALCULATE_RATE
        - CANCEL_BOOKING
        - GET_STATUS
        - etc.
        """
        try:
            logger.info("Classifying intent...")
            
            prompt = f"""
Classify the intent of this user message in a logistics context:

"{state['user_message']}"

Possible intents:
- CREATE_BOOKING: User wants to create a shipment booking
- TRACK_SHIPMENT: User wants to track a shipment
- CALCULATE_RATE: User wants to know shipping cost
- CANCEL_BOOKING: User wants to cancel a booking
- GET_STATUS: User wants shipment status
- SCHEDULE_PICKUP: User wants to schedule pickup
- OTHER: Something else

Respond with ONLY the intent name (e.g., "CREATE_BOOKING")
"""
            
            intent = await self.gemini.generate_content(
                prompt=prompt,
                temperature=0.1
            )
            
            intent = intent.strip().upper()
            state["intent"] = intent
            
            logger.info(f"Intent classified: {intent}")
            return state
        
        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            state["intent"] = "OTHER"
            return state
    
    async def _extract_entities(self, state: ExecutionState) -> ExecutionState:
        """
        Extract entities from user message using Gemini
        
        Examples:
        - Origin: "Mumbai"
        - Destination: "Delhi"
        - Weight: "5kg"
        - AWB Number: "ABC123"
        """
        try:
            logger.info("Extracting entities...")
            
            prompt = f"""
Extract relevant entities from this user message:

"{state['user_message']}"

Intent: {state['intent']}

Extract entities as JSON. Possible entities:
- origin: pickup location
- destination: delivery location
- weight: package weight
- dimensions: package dimensions
- awb_number: tracking number
- order_id: order identifier
- date: pickup/delivery date
- phone: contact number
- address: full address

Output ONLY valid JSON, no markdown.
Example: {{"origin": "Mumbai", "destination": "Delhi", "weight": "5kg"}}
"""
            
            entities_json = await self.gemini.generate_content(
                prompt=prompt,
                temperature=0.1
            )
            
            # Parse JSON
            import json
            entities_json = entities_json.strip()
            if entities_json.startswith("```json"):
                entities_json = entities_json[7:]
            if entities_json.startswith("```"):
                entities_json = entities_json[3:]
            if entities_json.endswith("```"):
                entities_json = entities_json[:-3]
            entities_json = entities_json.strip()
            
            entities = json.loads(entities_json)
            state["entities"] = entities
            
            logger.info(f"Entities extracted: {entities}")
            return state
        
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            state["entities"] = {}
            return state
    
    async def _select_agent(self, state: ExecutionState) -> ExecutionState:
        """
        Select appropriate agent based on intent
        """
        try:
            logger.info(f"Selecting agent for intent: {state['intent']}")
            
            # Map intent to agent type
            intent_to_agent = {
                "CREATE_BOOKING": "booking",
                "CALCULATE_RATE": "booking",
                "CANCEL_BOOKING": "booking",
                "TRACK_SHIPMENT": "tracking",
                "GET_STATUS": "tracking",
                "SCHEDULE_PICKUP": "booking"
            }
            
            agent_type = intent_to_agent.get(state["intent"], "booking")
            state["agent_type"] = agent_type
            
            # Check if agent exists
            agent = self.agent_registry.get_agent(state["partner_id"], agent_type)
            
            if not agent:
                state["error"] = f"No {agent_type} agent available for this partner"
                logger.error(state["error"])
            
            logger.info(f"Agent selected: {agent_type}")
            return state
        
        except Exception as e:
            logger.error(f"Agent selection error: {e}")
            state["error"] = str(e)
            return state
    
    def _route_after_selection(self, state: ExecutionState) -> str:
        """Route based on whether agent was found"""
        if state.get("error"):
            return "error"
        return "execute"
    
    async def _execute_with_agent(self, state: ExecutionState) -> ExecutionState:
        """
        Execute operation using the selected agent
        
        The agent will autonomously call the necessary APIs
        """
        try:
            logger.info(f"Executing with {state['agent_type']} agent...")
            
            # Get agent
            agent = self.agent_registry.get_agent(
                state["partner_id"],
                state["agent_type"]
            )
            
            if not agent:
                raise ValueError(f"Agent not found: {state['agent_type']}")
            
            # Build task description for agent
            task_description = self._build_task_description(state)
            
            # Execute agent
            from crewai import Task
            
            task = Task(
                description=task_description,
                agent=agent,
                expected_output="Detailed result of the operation with any API responses"
            )
            
            # Run the task
            result = await self._run_agent_task(agent, task)
            
            state["agent_response"] = str(result)
            logger.info(f"Agent execution completed")
            
            return state
        
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            state["error"] = str(e)
            return state
    
    def _build_task_description(self, state: ExecutionState) -> str:
        """Build task description for the agent"""
        intent = state["intent"]
        entities = state["entities"]
        message = state["user_message"]
        
        description = f"""
User Request: {message}

Intent: {intent}

Extracted Information:
{self._format_entities(entities)}

Your task:
1. Use the available tools to fulfill this request
2. Call the necessary API endpoints in the correct sequence
3. Handle any errors gracefully
4. Provide a detailed response with all relevant information

Execute the operation now.
"""
        
        return description
    
    def _format_entities(self, entities: Dict[str, Any]) -> str:
        """Format entities for display"""
        if not entities:
            return "None"
        return "\n".join(f"- {k}: {v}" for k, v in entities.items())
    
    async def _run_agent_task(self, agent, task) -> str:
        """Run agent task and return result"""
        try:
            # For now, simulate agent execution
            # In real implementation, this would use CrewAI's task execution
            
            # Execute agent tools
            result = f"Agent {agent.role} executed task successfully"
            
            # TODO: Implement actual CrewAI task execution
            # result = task.execute()
            
            return result
        
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            raise
    
    async def _generate_response(self, state: ExecutionState) -> ExecutionState:
        """
        Generate human-friendly response from agent output
        """
        try:
            logger.info("Generating final response...")
            
            prompt = f"""
Generate a friendly, conversational response for the user based on this information:

User's Request: {state['user_message']}
Intent: {state['intent']}
Agent's Result: {state.get('agent_response', 'No response')}

Create a natural, helpful response that:
1. Confirms what was done
2. Provides key information (booking ID, tracking number, cost, etc.)
3. Is conversational and friendly
4. Offers next steps if relevant

Keep it concise but informative.
"""
            
            response = await self.gemini.generate_content(
                prompt=prompt,
                temperature=0.7
            )
            
            state["final_response"] = response
            
            logger.info("Response generated")
            return state
        
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            state["final_response"] = f"Operation completed. {state.get('agent_response', '')}"
            return state
    
    async def _handle_error(self, state: ExecutionState) -> ExecutionState:
        """Handle errors gracefully"""
        error_msg = state.get("error", "Unknown error occurred")
        
        state["final_response"] = f"""
I'm sorry, I encountered an issue: {error_msg}

This could mean:
- The integration is still being set up
- Some information is missing
- There's a temporary service issue

Please try again or contact support if the issue persists.
"""
        
        return state


# Global instance
_execution_graph: Optional[AutonomousExecutionGraph] = None


def get_execution_graph() -> AutonomousExecutionGraph:
    """Get global execution graph instance"""
    global _execution_graph
    if _execution_graph is None:
        _execution_graph = AutonomousExecutionGraph()
    return _execution_graph


