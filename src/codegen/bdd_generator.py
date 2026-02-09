"""BDD/Gherkin feature file generator."""

from pathlib import Path
from typing import Dict, List


class BDDGenerator:
    """Generates Gherkin feature files from user stories."""

    def generate_feature_file(
        self,
        story: Dict,
        workspace: Path,
        language: str = "python"
    ) -> Path:
        """Generate a Gherkin feature file for a user story.

        Args:
            story: Story dict with id, title, description, acceptance_criteria, scenarios
            workspace: Workspace directory
            language: Programming language (for step definitions path)

        Returns:
            Path to generated feature file
        """
        story_id = story["id"]
        title = story["title"]
        description = story.get("description", "")

        # Create features directory
        features_dir = workspace / "features"
        features_dir.mkdir(exist_ok=True)

        # Generate feature content
        feature_content = self._build_feature_content(story)

        # Write feature file
        feature_file = features_dir / f"{story_id.lower()}.feature"
        feature_file.write_text(feature_content)

        return feature_file

    def _build_feature_content(self, story: Dict) -> str:
        """Build Gherkin feature file content."""
        lines = []

        # Feature header
        lines.append(f"Feature: {story['title']}")
        lines.append("")

        # Description
        if "description" in story:
            for line in story["description"].split("\n"):
                lines.append(f"  {line}")
            lines.append("")

        # Scenarios from story
        if "scenarios" in story and story["scenarios"]:
            for scenario in story["scenarios"]:
                lines.extend(self._build_scenario(scenario))
        else:
            # Generate from acceptance criteria if no scenarios provided
            lines.extend(self._build_scenarios_from_ac(story))

        return "\n".join(lines)

    def _build_scenario(self, scenario: Dict) -> List[str]:
        """Build a single Gherkin scenario."""
        lines = []

        lines.append(f"  Scenario: {scenario['name']}")

        # Given steps
        if "given" in scenario:
            for step in scenario["given"]:
                lines.append(f"    Given {step}")

        # When steps
        if "when" in scenario:
            for step in scenario["when"]:
                lines.append(f"    When {step}")

        # Then steps
        if "then" in scenario:
            for step in scenario["then"]:
                lines.append(f"    Then {step}")

        lines.append("")
        return lines

    def _build_scenarios_from_ac(self, story: Dict) -> List[str]:
        """Generate basic scenarios from acceptance criteria."""
        lines = []

        acceptance_criteria = story.get("acceptance_criteria", [])

        if acceptance_criteria:
            lines.append("  Scenario: Basic acceptance")

            # Simple scenario from first AC
            if len(acceptance_criteria) > 0:
                lines.append(f"    Given the system is ready")
                lines.append(f"    When I complete the feature")

                for ac in acceptance_criteria:
                    lines.append(f"    Then {ac}")

            lines.append("")

        return lines

    def generate_step_definitions_template(
        self,
        feature_file: Path,
        language: str = "python"
    ) -> Path:
        """Generate a template for step definitions.

        Args:
            feature_file: Path to feature file
            language: Programming language

        Returns:
            Path to step definitions file
        """
        if language == "python":
            return self._generate_python_steps(feature_file)
        else:
            raise ValueError(f"Language {language} not supported yet")

    def _generate_python_steps(self, feature_file: Path) -> Path:
        """Generate Python step definitions template (pytest-bdd style)."""
        workspace = feature_file.parent.parent
        steps_dir = workspace / "features" / "steps"
        steps_dir.mkdir(exist_ok=True)

        feature_name = feature_file.stem
        steps_file = steps_dir / f"{feature_name}_steps.py"

        # Parse feature file to extract step types
        content = feature_file.read_text()
        steps = self._extract_steps_from_feature(content)

        # Generate template
        template_lines = [
            '"""Step definitions for {}.feature"""'.format(feature_name),
            "",
            "import pytest",
            "from pytest_bdd import scenarios, given, when, then, parsers",
            "",
            "# Load scenarios from feature file",
            f'scenarios("../{feature_name}.feature")',
            "",
        ]

        # Add step definition stubs
        seen_steps = set()
        for step_type, step_text in steps:
            step_key = (step_type, step_text)
            if step_key in seen_steps:
                continue
            seen_steps.add(step_key)

            decorator = step_type.lower()
            func_name = self._step_text_to_function_name(step_text)

            template_lines.extend([
                f"@{decorator}('{step_text}')",
                f"def {func_name}():",
                f'    """TODO: Implement this step"""',
                "    pass",
                "",
            ])

        steps_file.write_text("\n".join(template_lines))
        return steps_file

    def _extract_steps_from_feature(self, content: str) -> List[tuple]:
        """Extract (step_type, step_text) from feature content."""
        steps = []
        for line in content.splitlines():
            line = line.strip()
            for step_type in ["Given", "When", "Then", "And"]:
                if line.startswith(step_type + " "):
                    step_text = line[len(step_type) + 1:]
                    steps.append((step_type, step_text))
        return steps

    def _step_text_to_function_name(self, step_text: str) -> str:
        """Convert step text to a Python function name."""
        # Simple conversion: lowercase, replace spaces with underscores
        import re
        name = step_text.lower()
        name = re.sub(r'[^a-z0-9_]+', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        return name[:50]  # Limit length
