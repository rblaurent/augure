#!/bin/bash
set -e

# Ensure custom skills directory exists
mkdir -p /workspace/custom/.opencode/skills

# Ensure all memory directories exist
mkdir -p \
    /workspace/memory/meta/invocation_logs \
    /workspace/memory/characters \
    /workspace/memory/players \
    /workspace/memory/scenes \
    /workspace/memory/arcs/actifs \
    /workspace/memory/arcs/clos \
    /workspace/memory/world/locations \
    /workspace/memory/world/factions \
    /workspace/memory/world/magic \
    /workspace/memory/world/history \
    /workspace/memory/media

# Seed identity.md on first start
if [ ! -f /workspace/config/identity.md ] && [ -f /workspace/config/seeds/identity.md ]; then
    cp /workspace/config/seeds/identity.md /workspace/config/identity.md
    echo "Seeded config/identity.md"
fi

# Seed guides.md on first start
if [ ! -f /workspace/config/guides.md ] && [ -f /workspace/config/seeds/guides.md ]; then
    cp /workspace/config/seeds/guides.md /workspace/config/guides.md
    echo "Seeded config/guides.md"
fi

# Seed style.md on first start
if [ ! -f /workspace/config/style.md ] && [ -f /workspace/config/seeds/style.md ]; then
    cp /workspace/config/seeds/style.md /workspace/config/style.md
    echo "Seeded config/style.md"
fi

exec python -m src.bot
