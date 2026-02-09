"""Unit tests for Sprint 0 infrastructure story generation."""

from pathlib import Path
import tempfile

from src.orchestrator.backlog import ProductMetadata
from src.orchestrator.sprint_zero import (
    SprintZeroGenerator,
    BrownfieldAnalyzer,
    InfrastructureStory,
)


class TestSprintZeroGenerator:
    """Test infrastructure story generation for Sprint 0."""

    def test_generate_python_stories(self):
        """Test generating Python infrastructure stories."""
        product_meta = ProductMetadata(
            name="Test Project",
            description="Test description",
            languages=["python"],
            tech_stack=["github-actions", "docker"],
            repository_type="greenfield",
            repository_url="",
        )

        generator = SprintZeroGenerator(product_meta, {})
        stories = generator.generate_stories()

        # Should have CI + Python linting + Python testing + Docker
        assert len(stories) >= 4

        story_ids = [s.id for s in stories]
        assert "INFRA-CI-GHA" in story_ids
        assert "INFRA-PY-LINT" in story_ids
        assert "INFRA-PY-TEST" in story_ids
        assert "INFRA-DOCKER" in story_ids

    def test_generate_multi_language_stories(self):
        """Test generating stories for multiple languages."""
        product_meta = ProductMetadata(
            name="Multi-Lang Project",
            description="Test",
            languages=["python", "go", "typescript"],
            tech_stack=["github-actions", "kubernetes"],
            repository_type="greenfield",
            repository_url="",
        )

        generator = SprintZeroGenerator(product_meta, {})
        stories = generator.generate_stories()

        story_ids = [s.id for s in stories]

        # Should have stories for all languages
        assert "INFRA-PY-LINT" in story_ids
        assert "INFRA-GO-LINT" in story_ids
        assert "INFRA-TS-LINT" in story_ids
        assert "INFRA-K8S" in story_ids

    def test_gitlab_ci_generation(self):
        """Test GitLab CI story generation when GitLab is in tech stack."""
        product_meta = ProductMetadata(
            name="GitLab Project",
            description="Test",
            languages=["python"],
            tech_stack=["gitlab-ci"],
            repository_type="greenfield",
            repository_url="",
        )

        generator = SprintZeroGenerator(product_meta, {})
        stories = generator.generate_stories()

        story_ids = [s.id for s in stories]
        assert "INFRA-CI-GITLAB" in story_ids
        assert "INFRA-CI-GHA" not in story_ids

    def test_convert_to_backlog_format(self):
        """Test converting InfrastructureStory to backlog format."""
        story = InfrastructureStory(
            id="TEST-001",
            title="Test Story",
            description="Test description",
            acceptance_criteria=["Criteria 1", "Criteria 2"],
            story_points=3,
            priority=1,
            assigned_specializations=["devops"],
            config_files=["test.yml"],
            validation_command="test command",
            template_content={"test.yml": "content"},
        )

        generator = SprintZeroGenerator(
            ProductMetadata("Test", "", [], [], "greenfield", ""), {}
        )
        backlog_format = generator.convert_to_backlog_format(story)

        assert backlog_format["id"] == "TEST-001"
        assert backlog_format["title"] == "Test Story"
        assert backlog_format["sprint"] == 0
        assert "_infrastructure" in backlog_format
        assert backlog_format["_infrastructure"]["config_files"] == ["test.yml"]


class TestBrownfieldAnalyzer:
    """Test brownfield repository analysis."""

    def test_analyze_empty_workspace(self):
        """Test analyzing an empty workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            analyzer = BrownfieldAnalyzer(workspace)
            analysis = analyzer.analyze()

            # All should be False for empty workspace
            assert analysis["ci_pipeline"] is False
            assert analysis["docker"] is False
            assert analysis["python_linting"] is False

    def test_analyze_with_github_actions(self):
        """Test detecting GitHub Actions CI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            gh_dir = workspace / ".github" / "workflows"
            gh_dir.mkdir(parents=True)
            (gh_dir / "ci.yml").write_text("name: CI")

            analyzer = BrownfieldAnalyzer(workspace)
            analysis = analyzer.analyze()

            assert analysis["ci_pipeline"] is True

    def test_analyze_with_docker(self):
        """Test detecting Docker configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "Dockerfile").write_text("FROM python:3.11")

            analyzer = BrownfieldAnalyzer(workspace)
            analysis = analyzer.analyze()

            assert analysis["docker"] is True

    def test_analyze_with_python_linting(self):
        """Test detecting Python linting configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            pyproject = workspace / "pyproject.toml"
            pyproject.write_text(
                """
[tool.black]
line-length = 88

[tool.ruff]
select = ["E", "F"]
"""
            )

            analyzer = BrownfieldAnalyzer(workspace)
            analysis = analyzer.analyze()

            assert analysis["python_linting"] is True

    def test_generate_gap_stories(self):
        """Test generating stories only for missing infrastructure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            # Create partial infrastructure (only Docker)
            (workspace / "Dockerfile").write_text("FROM python:3.11")

            analyzer = BrownfieldAnalyzer(workspace)
            analysis = analyzer.analyze()

            # Generate all possible stories
            all_stories = [
                InfrastructureStory(
                    id="INFRA-CI-GHA",
                    title="CI Pipeline",
                    description="",
                    acceptance_criteria=[],
                    story_points=5,
                    priority=1,
                    assigned_specializations=["devops"],
                    config_files=[],
                ),
                InfrastructureStory(
                    id="INFRA-DOCKER",
                    title="Docker Setup",
                    description="",
                    acceptance_criteria=[],
                    story_points=5,
                    priority=2,
                    assigned_specializations=["devops"],
                    config_files=[],
                ),
                InfrastructureStory(
                    id="INFRA-PY-LINT",
                    title="Python Linting",
                    description="",
                    acceptance_criteria=[],
                    story_points=3,
                    priority=3,
                    assigned_specializations=["backend"],
                    config_files=[],
                ),
            ]

            # Get gap stories (only missing infrastructure)
            gap_stories = analyzer.generate_gap_stories(analysis, all_stories)

            # Docker exists, so it should be excluded
            gap_ids = [s.id for s in gap_stories]
            assert "INFRA-CI-GHA" in gap_ids  # Missing
            assert "INFRA-PY-LINT" in gap_ids  # Missing
            assert "INFRA-DOCKER" not in gap_ids  # Exists


class TestProductMetadata:
    """Test ProductMetadata extraction from backlog."""

    def test_product_metadata_defaults(self):
        """Test ProductMetadata with default values."""
        meta = ProductMetadata(name="Test Project", description="Test description")

        assert meta.languages == []
        assert meta.tech_stack == []
        assert meta.repository_type == "greenfield"
        assert meta.repository_url == ""

    def test_product_metadata_full(self):
        """Test ProductMetadata with all fields."""
        meta = ProductMetadata(
            name="Full Project",
            description="Full description",
            languages=["python", "go"],
            tech_stack=["docker", "kubernetes"],
            repository_type="brownfield",
            repository_url="https://github.com/org/repo.git",
        )

        assert meta.name == "Full Project"
        assert len(meta.languages) == 2
        assert "python" in meta.languages
        assert "docker" in meta.tech_stack
        assert meta.repository_type == "brownfield"
