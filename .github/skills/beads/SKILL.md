---
name: beads
description: Beads CLI (bd) reference for lightweight issue tracking with first-class dependency support.
tools: ["terminal"]
---

# Beads CLI (bd)

Use `bd` for all task and issue tracking. Issues are chained together like beads with dependency support.

## Core Workflow Commands

### Quick Commands
```bash
bd ready                             # Find available work (no blockers)
bd update <id> --claim               # Claim work (sets assignee, status to in_progress)
bd close <id>                        # Complete work
bd sync                              # Sync with git (export to JSONL)
```

### View Tasks
```bash
bd list                              # List open issues (default limit: 50)
bd list --all                        # Include closed issues
bd list --status in_progress         # Filter by status
bd list --priority P0                # Filter by priority (P0-P4)
bd list --assignee @me               # Your assigned issues
bd list --ready                      # Ready to work (no blockers)
bd list --pretty                     # Tree format with status symbols
bd list --type epic                  # Filter by type
bd list --label bug                  # Filter by label (AND logic)
bd list --label-any bug,feature      # Filter by label (OR logic)
```

### View Issue Details
```bash
bd show <id>                         # Show issue details
bd show <id> --children              # Show with children
bd show <id> --refs                  # Show reverse references
```

### Create Issues
```bash
bd create "Fix dependency check"                # Simple task
bd create "Add feature" --type feature          # Specify type
bd create "P0 bug" --priority P0 --type bug     # With priority
bd create "Epic name" --type epic               # Create epic
bd create "Subtask" --parent <parent-id>        # Create child issue
```

### Update Issues
```bash
bd update <id> --status in_progress   # Start working
bd update <id> --status closed        # Complete task
bd update <id> --status blocked       # Blocked on dependencies
bd reopen <id>                        # Reopen closed issue
bd update <id> --claim                # Claim issue (assign + in_progress)
bd update <id> --assignee @me         # Assign to yourself
bd update <id> --priority P1          # Change priority
bd update <id> --add-label bug        # Add label
bd update <id> --title "New title"    # Update title
```

### Dependencies & Structure
```bash
bd dep <blocker-id> --blocks <blocked-id>  # Add blocking dependency
bd dep add <blocked-id> <blocker-id>       # Alternative syntax
bd dep list <id>                           # List dependencies
bd dep tree <id>                           # Show dependency tree
bd children <id>                           # List child issues (alias for bd list --parent <id>)
bd graph <id>                              # Show dependency graph
bd graph --all                             # Show graph for all open issues
bd epic status                             # Show epic completion status
bd epic close-eligible                     # Close epics where all children complete
```

### Search & Filter
```bash
bd search "dependency check"              # Text search (title, description, ID)
bd list --title-contains "test"           # Filter by title substring
bd list --created-after 2025-01-01        # Date filters
bd list --updated-after "1 week ago"      # Relative dates
```

## Advanced Features

### JSON Output
```bash
bd list --json                            # JSON array output
bd show <id> --json                       # JSON issue details
bd export                                 # Export to JSONL (one per line)
bd export --format jsonl                  # Same as above
bd export --format obsidian               # Export to Obsidian Tasks format
```

### Status & Statistics
```bash
bd status                                 # Database overview with activity
bd status --no-activity                   # Skip git activity (faster)
bd status --assigned                      # Show your assigned issues
bd count                                  # Count all issues
bd count --status open                    # Count by filter
bd count --by-status                      # Group count by status
bd count --by-priority                    # Group count by priority
bd count --by-type                        # Group count by type
bd stale                                  # Show stale issues (30+ days)
bd stale --days 14                        # Custom staleness threshold
```

### Export & Sync
```bash
bd export                                 # Export to JSONL (stdout)
bd export -o file.jsonl                   # Export to file
bd export --format obsidian               # Export to Obsidian markdown
bd sync                                   # Sync to JSONL (git-tracked)
bd sync --full                            # Full export with all metadata
```

## Common Filters

- `--status`: open, in_progress, blocked, deferred, closed
- `--type`: bug, feature, task, epic, chore
- `--priority`: P0 (highest) through P4 (lowest)
- `--assignee`: @me or username
- `--label`: Filter by labels (AND logic)

## Task Workflow Example

```bash
# 1. View available tasks
bd ready                             # Find work with no blockers
bd list --ready --pretty             # Alternative with tree view

# 2. Start work on a task
bd update <id> --status in_progress  # Claim work

# 3. View task details
bd show <id>

# 4. Mark complete
bd close <id>                        # Quick close
bd update <id> --status closed       # Alternative
```

## Session Completion (Landing the Plane)

When ending a work session, complete ALL steps:

1. **File issues for remaining work** - Create follow-up tasks
2. **Run quality gates** - `make lint && make test`
3. **Update issue status** - Close finished, update in-progress
4. **PUSH TO REMOTE** (MANDATORY):
   ```bash
   git pull --rebase
   bd sync                           # Sync beads to JSONL
   git push
   git status                        # Verify "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL**: Work is NOT complete until `git push` succeeds. Never stop before pushing.

## Setup

```bash
bd init                              # Initialize in repository
bd onboard                           # Get started guide
bd doctor                            # Check installation health
bd info                              # Show database info
```

## References
- GitHub: https://github.com/steveyegge/beads
- Install: `curl -sSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash`
