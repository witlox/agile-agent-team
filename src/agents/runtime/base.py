"""Base classes for agent runtimes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class RuntimeResult:
    """Result from a runtime execution."""

    success: bool
    content: str
    turns: int = 0
    tool_calls: List[Dict] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentRuntime(ABC):
    """Abstract base class for agent runtimes.

    A runtime handles the execution of tasks with tool use capabilities.
    Different runtimes can use different backends (Anthropic API, local vLLM, etc.)
    """

    def __init__(self, config: Dict, tools: List["Tool"]):
        """Initialize runtime with configuration and available tools.

        Args:
            config: Runtime-specific configuration dict
            tools: List of Tool instances available to the agent
        """
        self.config = config
        self.tools = {tool.name: tool for tool in tools}
        self.tool_list = tools

    @abstractmethod
    async def execute_task(
        self,
        system_prompt: str,
        user_message: str,
        max_turns: int = 20,
    ) -> RuntimeResult:
        """Execute a task with agentic tool use loop.

        The runtime should:
        1. Generate a response given the system prompt and user message
        2. Parse any tool calls from the response
        3. Execute requested tools
        4. Feed results back to the model
        5. Repeat until task is complete or max_turns reached

        Args:
            system_prompt: Agent's full system prompt (personality + context)
            user_message: The task/question from the user
            max_turns: Maximum number of generation turns

        Returns:
            RuntimeResult with execution outcome
        """
        pass

    async def _execute_tool(self, name: str, params: Dict) -> "ToolResult":
        """Execute a tool by name with given parameters.

        Args:
            name: Tool name
            params: Tool parameters

        Returns:
            ToolResult from tool execution
        """
        tool = self.tools.get(name)
        if tool is None:
            from ..agent_tools import ToolResult
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {name}"
            )

        try:
            return await tool.execute(**params)
        except Exception as e:
            from ..agent_tools import ToolResult
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution error: {str(e)}"
            )
