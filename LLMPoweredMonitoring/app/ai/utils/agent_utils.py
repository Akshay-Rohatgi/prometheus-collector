"""Utilities for AI agent creation and execution."""

from typing import Any, Callable, Optional, Dict, Tuple
from langchain_community.callbacks import get_openai_callback
from langgraph.prebuilt import create_react_agent
from printer import printer
from ..models import llm_41
from . import print_utils

class AgentManager:
    """Manages the creation and execution of AI agents."""

    @staticmethod
    def create_and_run_agent(prompt: str, tools: list = [], agent_prompt: Optional[str] = None, error_handler: Optional[Callable] = None) -> Tuple[Any, float]:
        """Create and run an AI agent with the specified configuration.

        Args:
            prompt: The prompt to send to the agent
            tools: List of tools available to the agent (default: [])
            agent_prompt: Optional custom prompt for agent creation
            error_handler: Optional custom error handler function

        Returns:
            Tuple containing:
                - The agent's response (or None if execution failed)
                - The total cost of the agent execution
        """
        agent = create_react_agent(
            llm_41,
            tools=tools,
            prompt=agent_prompt,
        )

        try:
            with get_openai_callback() as callback:
                response = agent.invoke(
                    {"messages": [{"role": "user", "content": prompt}]}
                )
                print_utils.print_token_stats(callback)
                return response, callback.total_cost
        except Exception as e:
            if error_handler:
                return error_handler(e)
            printer.error(f"Agent execution failed: {str(e)}")
            return None, 0.0

    @staticmethod
    def get_agent_response_content(response: Dict[str, Any], index: int = -1) -> Optional[str]:
        """Extract content from an agent response.

        Args:
            response: The response dictionary from the agent
            index: The index of the message to extract (default: -1 for last message)

        Returns:
            The content of the message at the specified index, or None if not found
        """
        try:
            return response["messages"][index].content
        except (KeyError, IndexError):
            return None
