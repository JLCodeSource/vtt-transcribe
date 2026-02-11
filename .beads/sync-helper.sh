#!/usr/bin/env bash
# BD Sync Helper - Automatically commit and push beads-sync changes
set -euo pipefail

# Export beads to JSONL
echo "=== Exporting beads to JSONL ==="
bd sync

# Check if there are changes in the worktree
cd .git/beads-worktrees/beads-sync

if [[ -z "$(git status --porcelain)" ]]; then
    echo "✓ No changes to sync"
    exit 0
fi

# Commit changes
echo "=== Committing changes ==="
PRE_COMMIT_ALLOW_NO_CONFIG=1 git add .beads/issues.jsonl .beads/beads.left.jsonl .beads/beads.left.meta.json .beads/sync-state.json 2>/dev/null || true

# Generate commit message
CHANGED_COUNT=$(git diff --cached --numstat | wc -l)
COMMIT_MSG="bd sync: auto-sync $(date +'%Y-%m-%d %H:%M:%S')"

PRE_COMMIT_ALLOW_NO_CONFIG=1 git commit -m "$COMMIT_MSG" || {
    echo "⚠️  No changes staged for commit"
    exit 0
}

# Push to remote
echo "=== Pushing to remote ==="
git push origin beads-sync

echo "✓ Sync complete!"
