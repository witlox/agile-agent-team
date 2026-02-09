# Agent Runtimes: Tool-Using Agents

**Date**: February 2026
**Status**: 🚧 Design

## Overview

Agents need tool use capabilities to produce real code. This system supports three deployment modes:

1. **Fully Anthropic** - Opus/Sonnet via API (requires internet)
2. **Fully Local** - vLLM with tool layer (offline, self-hosted)
3. **Hybrid** - Mix of both (cost optimization)

## Architecture

```
┌─────────────────────────────────────────────┐
│            BaseAgent                        │
│  (personality + seniority + specialization) │
└─────────────┬───────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────────┐
│         AgentRuntime (abstract)             │
│  - execute_task(task, tools)                │
│  - agentic_loop(messages, tools, max_turns) │
└─────────────┬───────────────────────────────┘
              │
      ┌───────┴────────┐
      ↓                ↓
┌─────────────┐  ┌──────────────┐
│ Anthropic   │  │ VLLMRuntime  │
│ Runtime     │  │              │
│             │  │              │
│ - MCP tools │  │ - Text-based │
│ - Native    │  │   tool calls │
│   function  │  │ - Local exec │
│   calling   │  │              │
└─────────────┘  └──────────────┘
```

## Configuration

### config.yaml

```yaml
experiment:
  runtime_mode: "hybrid"  # anthropic | local | hybrid

runtimes:
  anthropic:
    enabled: true
    api_key_env: "ANTHROPIC_API_KEY"
    default_model: "claude-sonnet-4-5"
    fallback_model: "claude-opus-4-6"  # For complex tasks
    mcp_enabled: true
    max_tokens: 8192

  local_vllm:
    enabled: true
    endpoint: "http://vllm-gh200-module-1:8000"
    tool_use_protocol: "xml"  # xml | json | hermes
    max_tokens: 8192

  # Shared tool configuration
  tools:
    workspace_root: "/workspace/agent-projects"
    git_enabled: true
    bash_enabled: true
    bash_timeout_seconds: 300
    allowed_commands:
      - "git"
      - "pytest"
      - "mypy"
      - "black"
      - "ruff"
      - "npm"
      - "docker"
    blocked_commands:
      - "rm -rf /"
      - "dd"
      - "mkfs"

# Agent runtime assignments
models:
  agents:
    ahmed_senior_dev_lead:
      runtime: "anthropic"  # Best model for lead
      model: "claude-opus-4-6"
      tools: ["filesystem", "git", "bash", "github", "search"]

    sophie_senior_qa_lead:
      runtime: "anthropic"
      model: "claude-sonnet-4-5"
      tools: ["filesystem", "git", "bash", "test_runner"]

    alex_senior_networking:
      runtime: "anthropic"
      model: "claude-sonnet-4-5"
      tools: ["filesystem", "git", "bash"]

    priya_senior_devops:
      runtime: "local_vllm"  # Local for cost savings
      model: "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
      tools: ["filesystem", "git", "bash"]

    marcus_mid_backend:
      runtime: "local_vllm"
      model: "Qwen/Qwen2.5-Coder-14B-Instruct"
      tools: ["filesystem", "git"]

    elena_mid_frontend:
      runtime: "local_vllm"
      model: "Qwen/Qwen2.5-Coder-14B-Instruct"
      tools: ["filesystem", "git"]

    jamie_junior_fullstack:
      runtime: "local_vllm"
      model: "Qwen/Qwen2.5-Coder-7B-Instruct"
      tools: ["filesystem"]  # Limited tools

    jordan_junior_backend:
      runtime: "local_vllm"
      model: "Qwen/Qwen2.5-Coder-7B-Instruct"
      tools: ["filesystem"]

    yuki_senior_tester_integration:
      runtime: "local_vllm"
      model: "Qwen/Qwen2.5-14B-Instruct"
      tools: ["filesystem", "bash", "test_runner"]

    maria_mid_tester_e2e:
      runtime: "local_vllm"
      model: "Qwen/Qwen2.5-14B-Instruct"
      tools: ["filesystem", "bash"]

    alex_senior_po:
      runtime: "anthropic"  # PO needs good planning
      model: "claude-sonnet-4-5"
      tools: ["filesystem"]  # Read-only for PO
```

### Override for Fully Local Mode

```bash
# Environment variable to force all agents to local
export AGENT_RUNTIME_MODE=local

# Or via CLI
python -m src.orchestrator.main --runtime local --sprints 10
```

### Override for Fully Anthropic Mode

```bash
export AGENT_RUNTIME_MODE=anthropic

# Override models
export ANTHROPIC_SENIOR_MODEL=claude-opus-4-6
export ANTHROPIC_JUNIOR_MODEL=claude-sonnet-4-5
```

## Tool System

### Base Tool Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None
    files_changed: List[str] = None

class Tool(ABC):
    """Base class for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for invocation."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """What this tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema for tool parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
```

### Core Tools

```python
class ReadFileTool(Tool):
    name = "read_file"
    description = "Read contents of a file"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to workspace"}
        },
        "required": ["path"]
    }

    async def execute(self, path: str) -> ToolResult:
        try:
            full_path = self.workspace / path
            content = full_path.read_text()
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class WriteFileTool(Tool):
    name = "write_file"
    description = "Write content to a file (creates if doesn't exist)"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"}
        },
        "required": ["path", "content"]
    }

    async def execute(self, path: str, content: str) -> ToolResult:
        try:
            full_path = self.workspace / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            return ToolResult(
                success=True,
                output=f"Wrote {len(content)} bytes to {path}",
                files_changed=[path]
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class EditFileTool(Tool):
    name = "edit_file"
    description = "Edit a file by replacing exact text match"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string", "description": "Exact text to replace"},
            "new_text": {"type": "string", "description": "Replacement text"}
        },
        "required": ["path", "old_text", "new_text"]
    }

class RunCommandTool(Tool):
    name = "bash"
    description = "Execute a shell command in the workspace"
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer", "default": 60}
        },
        "required": ["command"]
    }

    async def execute(self, command: str, timeout: int = 60) -> ToolResult:
        # Security: Check against allowed/blocked commands
        if not self._is_allowed(command):
            return ToolResult(
                success=False,
                output="",
                error=f"Command not allowed: {command}"
            )

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.workspace
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            return ToolResult(
                success=proc.returncode == 0,
                output=stdout.decode() + stderr.decode(),
                error=None if proc.returncode == 0 else f"Exit code: {proc.returncode}"
            )
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(success=False, output="", error="Command timeout")

class GitCommitTool(Tool):
    name = "git_commit"
    description = "Commit staged changes with a message"
    parameters = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "files": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["message"]
    }

class SearchCodeTool(Tool):
    name = "search_code"
    description = "Search for text patterns in code using ripgrep"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "default": "."},
            "file_type": {"type": "string", "description": "File extension filter"}
        },
        "required": ["pattern"]
    }

class RunTestsTool(Tool):
    name = "run_tests"
    description = "Run pytest tests and return results"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "tests/"},
            "verbose": {"type": "boolean", "default": false}
        }
    }
```

## Runtime Implementations

### 1. AnthropicRuntime (Online)

```python
class AnthropicRuntime(AgentRuntime):
    """Uses Claude API with native tool use + MCP servers."""

    def __init__(self, config: Dict, tools: List[Tool]):
        self.client = anthropic.AsyncAnthropic(
            api_key=os.environ.get(config["api_key_env"])
        )
        self.model = config["model"]
        self.tools = tools
        self.mcp_client = MCPClient(config.get("mcp_servers", []))

    async def execute_task(
        self,
        system_prompt: str,
        user_message: str,
        max_turns: int = 20
    ) -> RuntimeResult:
        """Agentic loop with Claude's native tool use."""

        messages = [{"role": "user", "content": user_message}]
        tool_schemas = [self._tool_to_anthropic_schema(t) for t in self.tools]

        for turn in range(max_turns):
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
                tools=tool_schemas
            )

            # Check if Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Execute tools
                tool_results = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        result = await self._execute_tool(
                            content_block.name,
                            content_block.input
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": result.output
                        })

                # Continue conversation with tool results
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

            elif response.stop_reason == "end_turn":
                # Task complete
                return RuntimeResult(
                    success=True,
                    content=self._extract_text(response.content),
                    turns=turn + 1,
                    tool_calls=self._extract_tool_calls(messages)
                )

        return RuntimeResult(
            success=False,
            content="Max turns reached",
            turns=max_turns
        )

    async def _execute_tool(self, name: str, params: Dict) -> ToolResult:
        """Execute tool by name."""
        tool = next((t for t in self.tools if t.name == name), None)
        if tool is None:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        return await tool.execute(**params)
```

### 2. VLLMRuntime (Offline)

```python
class VLLMRuntime(AgentRuntime):
    """Local vLLM with text-based tool use protocol."""

    def __init__(self, config: Dict, tools: List[Tool]):
        self.endpoint = config["endpoint"]
        self.tool_protocol = config.get("tool_use_protocol", "xml")
        self.tools = tools
        self.model = config["model"]

    async def execute_task(
        self,
        system_prompt: str,
        user_message: str,
        max_turns: int = 20
    ) -> RuntimeResult:
        """Agentic loop with text-based tool calls."""

        # Inject tool documentation into system prompt
        enhanced_prompt = self._build_tool_prompt(system_prompt)

        messages = [
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": user_message}
        ]

        for turn in range(max_turns):
            # Generate response
            response = await self._generate(messages)

            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                # No tools requested, task complete
                return RuntimeResult(
                    success=True,
                    content=response,
                    turns=turn + 1
                )

            # Execute tools
            tool_results = []
            for call in tool_calls:
                result = await self._execute_tool(call["name"], call["params"])
                tool_results.append(result)

            # Add results to conversation
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": self._format_tool_results(tool_results)
            })

        return RuntimeResult(
            success=False,
            content="Max turns reached",
            turns=max_turns
        )

    def _build_tool_prompt(self, system_prompt: str) -> str:
        """Add tool documentation to system prompt."""

        if self.tool_protocol == "xml":
            tools_doc = self._format_tools_xml()
        elif self.tool_protocol == "json":
            tools_doc = self._format_tools_json()
        else:
            tools_doc = self._format_tools_hermes()

        return f"""{system_prompt}

# Available Tools

You have access to the following tools to complete your task:

{tools_doc}

## How to Use Tools

{self._get_protocol_instructions()}

## Important Rules

- Use tools to read, write, and edit code files
- Run tests after making changes
- Iterate on failures until tests pass
- Always verify your changes with read_file before committing
- Use git_commit when ready to save your work
"""

    def _format_tools_xml(self) -> str:
        """Format tools in XML style (works well with Qwen/DeepSeek)."""
        tools_xml = []
        for tool in self.tools:
            params = "\n".join(
                f"    <{k}>{v['description']}</{k}>"
                for k, v in tool.parameters["properties"].items()
            )
            tools_xml.append(f"""
<tool name="{tool.name}">
  <description>{tool.description}</description>
  <parameters>
{params}
  </parameters>
</tool>
""")
        return "\n".join(tools_xml)

    def _get_protocol_instructions(self) -> str:
        if self.tool_protocol == "xml":
            return """
To use a tool, output XML in this format:

<tool_call>
  <name>tool_name</name>
  <arguments>
    <param1>value1</param1>
    <param2>value2</param2>
  </arguments>
</tool_call>

Example:
<tool_call>
  <name>read_file</name>
  <arguments>
    <path>src/main.py</path>
  </arguments>
</tool_call>

You can call multiple tools in sequence. After each tool execution, you'll receive the result and can decide what to do next.
"""
        # ... other protocol formats

    def _parse_tool_calls(self, text: str) -> List[Dict]:
        """Parse tool calls from model response."""
        if self.tool_protocol == "xml":
            return self._parse_xml_tool_calls(text)
        # ... other parsers

    def _parse_xml_tool_calls(self, text: str) -> List[Dict]:
        """Parse XML tool calls."""
        import xml.etree.ElementTree as ET
        calls = []

        # Find all <tool_call> blocks
        pattern = r"<tool_call>(.*?)</tool_call>"
        matches = re.findall(pattern, text, re.DOTALL)

        for match in matches:
            try:
                root = ET.fromstring(f"<tool_call>{match}</tool_call>")
                name = root.find("name").text
                args_elem = root.find("arguments")
                params = {
                    child.tag: child.text
                    for child in args_elem
                }
                calls.append({"name": name, "params": params})
            except Exception as e:
                continue  # Skip malformed tool calls

        return calls

    async def _generate(self, messages: List[Dict]) -> str:
        """Call vLLM completion endpoint."""
        # Build prompt from messages
        prompt = self._messages_to_prompt(messages)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.endpoint}/v1/completions",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": 8192,
                    "temperature": 0.7,
                    "stop": ["</tool_call>", "\n\nUser:", "\n\nHuman:"]
                }
            )
            return response.json()["choices"][0]["text"]
```

## Tool Use Protocol Examples

### XML Protocol (Qwen/DeepSeek)

**Agent output:**
```xml
Let me read the current implementation first.

<tool_call>
  <name>read_file</name>
  <arguments>
    <path>src/api/users.py</path>
  </arguments>
</tool_call>
```

**System response:**
```
Tool result (read_file):
SUCCESS: Read 45 lines from src/api/users.py

def get_user(user_id: int):
    # TODO: implement
    pass
```

**Agent continues:**
```xml
I see the function is a stub. Let me implement it:

<tool_call>
  <name>edit_file</name>
  <arguments>
    <path>src/api/users.py</path>
    <old_text>def get_user(user_id: int):
    # TODO: implement
    pass</old_text>
    <new_text>def get_user(user_id: int):
    """Fetch user by ID from database."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user</new_text>
  </arguments>
</tool_call>
```

### JSON Protocol (Alternative)

```json
{
  "tool": "run_tests",
  "arguments": {
    "path": "tests/test_users.py",
    "verbose": true
  }
}
```

## Deployment Modes

### Mode 1: Fully Anthropic (Online)

```bash
# All agents use Claude
python -m src.orchestrator.main \
  --runtime anthropic \
  --sprints 10 \
  --output results/anthropic-run
```

**Cost**: ~$3-4 per sprint × 11 agents = **$30-40 per sprint**
**Quality**: Highest (native tool use, best coding abilities)

### Mode 2: Fully Local (Offline)

```bash
# All agents use vLLM
python -m src.orchestrator.main \
  --runtime local \
  --sprints 10 \
  --output results/local-run
```

**Cost**: **$0** (just GPU/electricity)
**Quality**: Good (depends on model, text-based tools)

### Mode 3: Hybrid (Mixed)

```bash
# Use config.yaml runtime assignments
python -m src.orchestrator.main \
  --runtime hybrid \
  --sprints 10 \
  --output results/hybrid-run
```

**Cost**: ~$3.50 per sprint (3-4 Claude agents)
**Quality**: Balanced (best of both)

---

## Next Steps

Should I implement this architecture? The order would be:

1. **Runtime abstraction** (`src/agents/runtime/`)
   - `base.py` - AgentRuntime abstract class
   - `anthropic_runtime.py` - Claude API implementation
   - `vllm_runtime.py` - Local vLLM implementation

2. **Tool system** (`src/tools/agent_tools/`)
   - `base.py` - Tool interface
   - `filesystem.py` - Read/Write/Edit/Search
   - `git.py` - Git operations
   - `bash.py` - Command execution
   - `test_runner.py` - Pytest integration

3. **Update BaseAgent** to use runtime
   - Remove direct vLLM calls
   - Delegate to runtime.execute_task()

4. **Configuration loading**
   - Parse runtime configs
   - Environment variable overrides
   - CLI flags for mode selection

5. **Integration testing**
   - Test each runtime separately
   - Test tool execution
   - Test offline mode works

Should I start implementing?
