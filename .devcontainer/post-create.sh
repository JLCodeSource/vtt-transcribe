#!/usr/bin/env bash
set -euo pipefail

# Use the project’s make target to install uv, create venv, and sync deps
make install-all

# Quick sanity output
uv run python -V

# Add Home Local to PATH
export PATH="$PATH:$HOME/.local/bin"

# Install beads CLI for issue tracking (downloads pre-built binary from GitHub releases)
echo "Installing beads (bd)..."
if ! command -v bd &> /dev/null; then
    curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
    
    # The install script places the binary in ~/.local/bin (no Go required)
    # Add to PATH if needed
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        export PATH="$PATH:$HOME/.local/bin"
        echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
    fi
    
    # Verify installation
    if command -v bd &> /dev/null; then
        echo "✓ beads installed: $(bd version)"
    else
        echo "⚠ beads installation completed but 'bd' not found in PATH"
    fi
else
    echo "✓ beads already installed: $(bd version)"
fi
