FROM python:3.11-slim-bookworm

LABEL maintainer="agile-agent-team"
LABEL description="Agile Agent Team - Multi-agent software development simulation"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r agentrunner && useradd -r -g agentrunner -m agentrunner

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and configuration
COPY src/ ./src/
COPY team_config/ ./team_config/
COPY config.yaml .
COPY backlog.yaml .
COPY examples/ ./examples/

# Set ownership
RUN chown -R agentrunner:agentrunner /app

# Create workspace directories writable by agentrunner
RUN mkdir -p /tmp/agent-workspace /app/outputs \
    && chown -R agentrunner:agentrunner /tmp/agent-workspace /app/outputs

USER agentrunner

# Metrics (Prometheus) and stakeholder webhook callback
EXPOSE 8080 8081

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/metrics || exit 1

CMD ["python", "-m", "src.orchestrator.main"]
