# Contributing Guide

Thank you for your interest in contributing to the Agile Agent Team experiment!

## Quick Start for Contributors

### Ways to Contribute

1. **Run experiments and share results**
   - Test different configurations
   - Report findings
   - Share velocity curves and metrics

2. **Improve agent profiles**
   - Enhance cognitive patterns
   - Add more realistic behaviors
   - Refine specializations

3. **Extend the system**
   - Add new agent roles
   - Implement additional metrics
   - Create new process rules

4. **Fix bugs**
   - Report issues with clear reproduction steps
   - Submit fixes with tests
   - Improve error handling

5. **Improve documentation**
   - Fix typos or unclear sections
   - Add examples
   - Translate to other languages

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub first, then:
gh repo clone YOUR_USERNAME/agile-agent-team
cd agile-agent-team
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install pytest black mypy ruff
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## Making Changes

### Code Style

We follow standard Python conventions:

```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

### Agent Profiles

When modifying agent profiles in `team_config/`:

1. **Maintain structure**: Follow existing profile format
2. **Be specific**: Concrete examples over abstract descriptions
3. **Add reasoning**: Explain *why* the agent behaves this way
4. **Test behavior**: Run qualification tests after changes

Example:
```bash
# After modifying a junior profile
./scripts/qualify-all-agents.sh --mock
```

### Source Code

When modifying Python code:

1. **Add docstrings**: All functions and classes
2. **Write tests**: Cover new functionality
3. **Update metrics**: If adding new behaviors
4. **Keep it simple**: Prefer clarity over cleverness

Example:
```python
def my_new_function(param: str) -> int:
    """
    Brief description of what this does.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
    """
    # Implementation
    pass
```

### Documentation

When updating docs:

1. **Be clear**: Write for someone new to the project
2. **Add examples**: Code snippets help
3. **Update related docs**: Keep consistency
4. **Check formatting**: Markdown should render correctly

## Running Tests

### Unit Tests

```bash
# Run all tests
pytest tests/unit/

# Run specific test
pytest tests/unit/test_kanban.py
```

### Integration Tests

```bash
pytest tests/integration/
```

### Qualification Tests

```bash
# Test all agents (mock mode)
./scripts/qualify-all-agents.sh --mock

# Test all agents against live vLLM
./scripts/qualify-all-agents.sh --vllm-endpoint http://<host>:8000
```

### Tool and Runtime Tests

```bash
# Test tool execution (filesystem, git, bash)
pytest tests/unit/test_runtime.py -v

# Test code generation workflow
pytest tests/integration/test_agent_codegen.py -v

# Test sprint integration with code generation
pytest tests/integration/test_sprint_codegen.py -v
```

## Submitting Changes

### 1. Commit Your Changes

```bash
# Stage changes
git add .

# Commit with clear message
git commit -m "Add: Brief description of what changed"
```

**Commit message format:**
- `Add: ...` - New feature
- `Fix: ...` - Bug fix
- `Improve: ...` - Enhancement
- `Docs: ...` - Documentation only
- `Refactor: ...` - Code restructuring

### 2. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 3. Create Pull Request

1. Go to the original repository on GitHub
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill in the template:

```markdown
## Description
Brief summary of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Agent profile enhancement

## Testing
- [ ] All existing tests pass
- [ ] Added tests for new functionality
- [ ] Ran qualification tests if agents modified

## Related Issues
Fixes #123
```

## Contribution Areas

### High Priority

1. **Model qualification tests** - Verify more models work with tool calling
2. **Code generation improvements** - Better BDD scenarios, test iteration strategies
3. **Additional metrics** - Track code quality, test effectiveness
4. **Performance optimization** - Reduce sprint wall-clock time
5. **Real repository integration** - Work with existing GitHub/GitLab projects

### Medium Priority

1. **More agent personalities** - Expand team diversity
2. **Integration with GitHub** - Use real repositories
3. **Additional disturbances** - More realistic failure modes
4. **Grafana dashboards** - Better visualizations

### Low Priority (Nice to Have)

1. **Web UI** - Monitor experiments visually
2. **Multi-team experiments** - Test coordination
3. **Historical data analysis** - Compare with human teams
4. **Alternative models** - Test Llama, Mistral, etc.

## Experiment Results Contributions

If you run experiments, please share:

### What to Share

1. **Configuration used**
   ```yaml
   # Your config.yaml settings
   profile_swapping: constrained
   sprints: 20
   # ...
   ```

2. **Key findings**
   - Velocity trends (with charts if possible)
   - Interesting team dynamics
   - Unexpected behaviors
   - Failure modes encountered

3. **Raw data** (if comfortable sharing)
   - Artifacts from `outputs/`
   - Prometheus metrics export
   - Interesting pairing dialogues

### Where to Share

- **GitHub Discussions** - For questions and results
- **Issues** - For bugs or feature requests
- **Pull Requests** - For code contributions
- **Blog posts** - Link in discussions

## Code of Conduct

### Our Standards

- Be respectful and constructive
- Welcome newcomers
- Focus on what's best for the project
- Show empathy toward others

### Unacceptable

- Harassment or discriminatory language
- Personal attacks
- Publishing others' private information
- Unconstructive criticism

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bug reports**: Open an Issue with reproduction steps
- **Feature ideas**: Open an Issue with use case
- **Implementation help**: Ask in Discussions

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Acknowledged in publications (if significant contribution)

## License

By contributing, you agree that your contributions will be licensed under the MIT License (same as the project).

---

## Quick Reference

```bash
# Setup
git clone YOUR_FORK
cd agile-agent-team
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Make changes
git checkout -b feature/my-feature
# ... edit files ...
black src/ && ruff check src/
pytest

# Submit
git commit -am "Add: My feature"
git push origin feature/my-feature
# Create PR on GitHub
```

## Common Tasks

### Add New Agent Role

1. Copy existing profile: `cp team_config/02_individuals/dev_sr_networking.md team_config/02_individuals/dev_sr_NEW.md`
2. Modify profile (specialization, cognitive patterns, etc.)
3. Add model config entry under `models.agents` in `config.yaml`
4. Run qualification tests: `./scripts/qualify-all-agents.sh --mock`

The factory autodiscovers profiles via glob — no code registration needed.

### Add New Metric

1. Define in `src/metrics/custom_metrics.py`
   ```python
   my_metric = Counter('my_metric_total', 'Description', ['label'])
   ```
2. Instrument in relevant code
   ```python
   my_metric.labels(label='value').inc()
   ```
3. Add to Grafana dashboard (optional)
4. Document in ARCHITECTURE.md

### Add New Process Rule

1. Create file: `team_config/03_process_rules/my_rule.md`
2. Document the rule clearly with examples
3. Update orchestrator if enforcement needed
4. Add tests to verify rule is followed
5. Update ARCHITECTURE.md

### Add New Tool for Agents

1. Create tool class in `src/tools/agent_tools/`
   ```python
   class MyTool(Tool):
       @property
       def name(self) -> str:
           return "my_tool"

       @property
       def description(self) -> str:
           return "What this tool does"

       @property
       def parameters(self) -> Dict[str, Any]:
           return {"type": "object", "properties": {...}}

       async def execute(self, **kwargs) -> ToolResult:
           # Implementation
           pass
   ```

2. Register in `src/tools/agent_tools/factory.py`
   ```python
   TOOL_REGISTRY = {
       "my_tool": MyTool,
       # ... existing tools
   }
   ```

3. Add to tool sets if appropriate
   ```python
   TOOL_SETS = {
       "my_set": ["my_tool", "other_tool"],
       # ... existing sets
   }
   ```

4. Test the tool
   ```python
   # tests/unit/test_my_tool.py
   async def test_my_tool():
       tool = MyTool(workspace_root="/tmp/test")
       result = await tool.execute(param="value")
       assert result.success
   ```

5. Add to agent configs in `config.yaml`
   ```yaml
   models:
     agents:
       alex_senior_networking:
         tools: ["filesystem", "git", "my_tool"]
   ```

---

**Thank you for contributing to advancing our understanding of AI team dynamics!**
