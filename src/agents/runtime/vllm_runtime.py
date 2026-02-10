"""vLLM runtime with text-based tool use protocol."""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List

import httpx

from .base import AgentRuntime, RuntimeResult
from ...tools.agent_tools import Tool, ToolResult


class VLLMRuntime(AgentRuntime):
    """Local vLLM runtime with XML-based tool calling.

    This runtime works fully offline using self-hosted vLLM models.
    Tool calls are parsed from XML tags in the model's text output.
    """

    def __init__(self, config: Dict, tools: List[Tool]):
        super().__init__(config, tools)
        self.endpoint = config["endpoint"]
        self.model = config["model"]
        self.tool_protocol = config.get("tool_use_protocol", "xml")
        self.max_tokens = config.get("max_tokens", 8192)
        self.temperature = config.get("temperature", 0.7)

    async def execute_task(
        self,
        system_prompt: str,
        user_message: str,
        max_turns: int = 20,
    ) -> RuntimeResult:
        """Execute task with agentic loop using text-based tool calls."""

        # Check for mock mode
        if self._is_mock_mode():
            return self._mock_execute(system_prompt, user_message)

        # Build enhanced system prompt with tool documentation
        enhanced_prompt = self._build_tool_prompt(system_prompt)

        conversation = [
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": user_message},
        ]

        all_tool_calls: List[Dict] = []
        files_changed: List[str] = []

        for turn in range(max_turns):
            # Generate response
            response = await self._generate(conversation)

            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                # No tools requested, task complete
                return RuntimeResult(
                    success=True,
                    content=response,
                    turns=turn + 1,
                    tool_calls=all_tool_calls,
                    files_changed=files_changed,
                )

            # Execute tools
            tool_results = []
            for call in tool_calls:
                result = await self._execute_tool(call["name"], call["params"])
                tool_results.append(
                    {"tool": call["name"], "params": call["params"], "result": result}
                )
                all_tool_calls.append(call)

                # Track files changed
                if result.files_changed:
                    files_changed.extend(result.files_changed)

            # Add to conversation
            conversation.append({"role": "assistant", "content": response})
            conversation.append(
                {"role": "user", "content": self._format_tool_results(tool_results)}
            )

        # Max turns reached
        return RuntimeResult(
            success=False,
            content=conversation[-2]["content"],  # Last assistant message
            turns=max_turns,
            tool_calls=all_tool_calls,
            files_changed=files_changed,
            error="Maximum turns reached without task completion",
        )

    def _build_tool_prompt(self, system_prompt: str) -> str:
        """Enhance system prompt with tool documentation."""
        if not self.tools:
            return system_prompt

        tools_doc = self._format_tools_xml()
        protocol_instructions = self._get_protocol_instructions()

        return f"""{system_prompt}

---

# Available Tools

You have access to the following tools to complete coding tasks:

{tools_doc}

{protocol_instructions}

## Tool Use Rules

1. **Read before writing**: Always read a file before editing it
2. **Verify changes**: Read files after editing to confirm changes
3. **Run tests**: Execute tests after making code changes
4. **Iterate on failures**: If tests fail, read the error, fix the code, and re-run
5. **Git workflow**: Stage and commit files after successful changes
6. **Multiple tools**: You can call multiple tools in sequence
7. **Stop when done**: When the task is complete, provide a summary without tool calls

## Example Workflow

1. read_file: Review existing code
2. edit_file: Make necessary changes
3. bash: Run tests (pytest tests/)
4. read_file: Check test output if needed
5. git_add: Stage changed files
6. git_commit: Commit with descriptive message
7. Provide final summary
"""

    def _format_tools_xml(self) -> str:
        """Format available tools as XML documentation."""
        tools_xml = []

        for tool in self.tool_list:
            params_doc = []
            schema = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])

            for param_name, param_info in schema.items():
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", "")
                required_mark = " (required)" if param_name in required else ""

                params_doc.append(
                    f'    <{param_name} type="{param_type}"{required_mark}>{param_desc}</{param_name}>'
                )

            params_str = (
                "\n".join(params_doc) if params_doc else "    <no parameters needed/>"
            )

            tools_xml.append(
                f"""
<tool name="{tool.name}">
  <description>{tool.description}</description>
  <parameters>
{params_str}
  </parameters>
</tool>"""
            )

        return "\n".join(tools_xml)

    def _get_protocol_instructions(self) -> str:
        """Get instructions for tool calling protocol."""
        return """
## How to Call Tools

To use a tool, output an XML block in this exact format:

```
<tool_call>
  <name>tool_name</name>
  <arguments>
    <param_name>value</param_name>
  </arguments>
</tool_call>
```

### Examples

**Read a file:**
```
<tool_call>
  <name>read_file</name>
  <arguments>
    <path>src/main.py</path>
  </arguments>
</tool_call>
```

**Edit a file:**
```
<tool_call>
  <name>edit_file</name>
  <arguments>
    <path>src/api.py</path>
    <old_text>def process():
    pass</old_text>
    <new_text>def process():
    return "implemented"</new_text>
  </arguments>
</tool_call>
```

**Run tests:**
```
<tool_call>
  <name>bash</name>
  <arguments>
    <command>pytest tests/ -v</command>
  </arguments>
</tool_call>
```

After each tool call, you'll receive the result. Then continue with next steps or provide your final answer.
"""

    def _parse_tool_calls(self, text: str) -> List[Dict]:
        """Parse XML tool calls from model output."""
        if self.tool_protocol == "xml":
            return self._parse_xml_tool_calls(text)
        else:
            # Future: support JSON or other protocols
            return []

    def _parse_xml_tool_calls(self, text: str) -> List[Dict]:
        """Parse XML-formatted tool calls."""
        calls = []

        # Find all <tool_call> blocks
        pattern = r"<tool_call>(.*?)</tool_call>"
        matches = re.findall(pattern, text, re.DOTALL)

        for match in matches:
            try:
                root = ET.fromstring(f"<tool_call>{match}</tool_call>")

                name_elem = root.find("name")
                if name_elem is None or not name_elem.text:
                    continue

                name = name_elem.text.strip()

                # Parse arguments
                args_elem = root.find("arguments")
                params = {}

                if args_elem is not None:
                    for child in args_elem:
                        # Handle text content, preserving whitespace for code
                        value = child.text or ""
                        params[child.tag] = value

                calls.append({"name": name, "params": params})

            except ET.ParseError:
                # Skip malformed XML
                continue

        return calls

    def _format_tool_results(self, results: List[Dict]) -> str:
        """Format tool results for model consumption."""
        formatted = []

        for item in results:
            tool_name = item["tool"]
            result: ToolResult = item["result"]

            if result.success:
                status = "SUCCESS"
                content = result.output
            else:
                status = "ERROR"
                content = result.error or "Unknown error"

            formatted.append(
                f"""
Tool: {tool_name}
Status: {status}
Output:
{content}
"""
            )

        return "\n".join(formatted)

    async def _generate(self, conversation: List[Dict]) -> str:
        """Generate response from vLLM."""
        # Build prompt from conversation
        prompt = self._messages_to_prompt(conversation)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.endpoint}/v1/completions",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "stop": ["</tool_call>", "\n\nUser:", "\n\nHuman:"],
                    },
                )

                if response.status_code != 200:
                    raise Exception(f"vLLM returned status {response.status_code}")

                data = response.json()
                return data["choices"][0]["text"]

        except Exception as e:
            raise Exception(f"Error calling vLLM: {str(e)}")

    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """Convert message list to prompt string."""
        parts = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"\n\nUser: {content}")
            elif role == "assistant":
                parts.append(f"\n\nAssistant: {content}")

        parts.append("\n\nAssistant:")
        return "".join(parts)

    def _is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return os.environ.get(
            "MOCK_LLM", ""
        ).lower() == "true" or self.endpoint.startswith("mock://")

    def _mock_execute(self, system_prompt: str, user_message: str) -> RuntimeResult:
        """Mock execution for testing without vLLM."""
        # Simple mock: pretend to write a file
        mock_response = f"I've analyzed the task: {user_message[:100]}...\n\n"
        mock_response += "Created implementation in src/example.py"

        return RuntimeResult(
            success=True,
            content=mock_response,
            turns=1,
            tool_calls=[{"name": "write_file", "params": {"path": "src/example.py"}}],
            files_changed=["src/example.py"],
        )
