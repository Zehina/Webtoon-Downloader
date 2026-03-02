#! /usr/bin/env bash

set -euo pipefail

# Install uv if missing
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies (default groups are configured in pyproject.toml)
uv sync

# Install pre-commit hooks
uv run pre-commit install --install-hooks
