FROM python:3.12-slim

# Install system dependencies + Node.js (required for OpenCode CLI)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install OpenCode CLI (ACP agent)
# TODO: replace with correct package name once confirmed
# Options: npm install -g opencode-ai  OR  npm install -g @opencode-ai/cli
RUN npm install -g opencode-ai

# Create non-root user
RUN useradd -m -u 1000 botuser

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Workspace directories (will be overridden by volume mounts)
RUN mkdir -p \
    /workspace/memory/meta \
    /workspace/memory/characters \
    /workspace/memory/players \
    /workspace/memory/scenes \
    /workspace/memory/arcs \
    /workspace/memory/world \
    /workspace/memory/media \
    /workspace/config \
    /workspace/workflows \
    /workspace/skills \
    /workspace/custom \
    /workspace/music \
    && chown -R botuser:botuser /workspace /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER botuser

ENTRYPOINT ["/entrypoint.sh"]
