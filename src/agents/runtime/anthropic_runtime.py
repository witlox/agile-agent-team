"""Anthropic (Claude) runtime with native tool use support."""

import os
from typing import Dict, List

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base import AgentRuntime, RuntimeResult
from ...tools.agent_tools import Tool, ToolResult


class AnthropicRuntime(AgentRuntime):
    """Claude API runtime with native tool use.

    Uses Anthropic's Messages API with built-in function calling.
    Requires internet connection and API key.
    """

    def __init__(self, config: Dict, tools: List[Tool]):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

        super().__init__(config, tools)

        api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
        api_key = os.environ.get(api_key_env)

        if not api_key:
            raise ValueError(
                f"Anthropic API key not found in environment variable: {api_key_env}"
            )

        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = config.get("model", "claude-sonnet-4-5")
        self.max_tokens = config.get("max_tokens", 8192)

    async def execute_task(
        self,
        system_prompt: str,
        user_message: str,
        max_turns: int = 20,
    ) -> RuntimeResult:
        """Execute task using Claude's native tool use."""

        # Convert tools to Anthropic's format
        tool_schemas = [self._tool_to_anthropic_schema(t) for t in self.tool_list]

        # Add native web search server tool if enabled
        if self.config.get("web_search_enabled", False):
            tool_schemas.append(
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": self.config.get("web_search_max_uses", 5),
                }
            )

        messages = [{"role": "user", "content": user_message}]

        all_tool_calls = []
        files_changed = []

        for turn in range(max_turns):
            # Call Claude API
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt,
                    messages=messages,
                    tools=tool_schemas if tool_schemas else anthropic.NOT_GIVEN,
                )
            except Exception as e:
                return RuntimeResult(
                    success=False,
                    content="",
                    turns=turn + 1,
                    error=f"API error: {str(e)}",
                )

            # Check stop reason
            if response.stop_reason == "tool_use":
                # Claude wants to use tools
                tool_results = []

                for content_block in response.content:
                    if content_block.type == "tool_use":
                        # Skip native server tools (web_search) — their
                        # results come back as separate content blocks that
                        # the API handles automatically.
                        if content_block.name == "web_search" and self.config.get(
                            "web_search_enabled", False
                        ):
                            all_tool_calls.append(
                                {
                                    "name": "web_search",
                                    "params": content_block.input,
                                }
                            )
                            continue

                        # Execute local tool
                        result = await self._execute_tool(
                            content_block.name, content_block.input
                        )

                        all_tool_calls.append(
                            {"name": content_block.name, "params": content_block.input}
                        )

                        if result.files_changed:
                            files_changed.extend(result.files_changed)

                        # Format result for Claude
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": self._format_tool_result(result),
                            }
                        )

                # Add assistant message and tool results to conversation
                messages.append({"role": "assistant", "content": response.content})
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})  # type: ignore[dict-item]

            elif response.stop_reason == "end_turn":
                # Task complete
                final_text = self._extract_text_from_response(response.content)

                return RuntimeResult(
                    success=True,
                    content=final_text,
                    turns=turn + 1,
                    tool_calls=all_tool_calls,
                    files_changed=files_changed,
                )

            elif response.stop_reason == "max_tokens":
                # Hit token limit
                final_text = self._extract_text_from_response(response.content)

                return RuntimeResult(
                    success=False,
                    content=final_text,
                    turns=turn + 1,
                    tool_calls=all_tool_calls,
                    files_changed=files_changed,
                    error="Hit max tokens limit",
                )

            else:
                # Unexpected stop reason
                return RuntimeResult(
                    success=False,
                    content="",
                    turns=turn + 1,
                    error=f"Unexpected stop reason: {response.stop_reason}",
                )

        # Max turns reached
        return RuntimeResult(
            success=False,
            content=messages[-1]["content"] if messages else "",
            turns=max_turns,
            tool_calls=all_tool_calls,
            files_changed=files_changed,
            error="Maximum turns reached",
        )

    def _tool_to_anthropic_schema(self, tool: Tool) -> Dict:
        """Convert Tool to Anthropic's tool schema format."""
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }

    def _format_tool_result(self, result: ToolResult) -> str:
        """Format ToolResult for Claude."""
        if result.success:
            return result.output
        else:
            return f"ERROR: {result.error}"

    def _extract_text_from_response(self, content: List) -> str:
        """Extract text content from Claude's response."""
        text_parts = []

        for block in content:
            if block.type == "text":
                text_parts.append(block.text)

        return "\n".join(text_parts)
