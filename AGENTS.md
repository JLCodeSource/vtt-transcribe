# Agent Instructions

## Issue Tracking

This project uses **bd (beads)** for issue tracking.
Run `bd prime` for workflow context, or install hooks (`bd hooks install`) for auto-injection.

**Quick reference:**
- `bd ready` - Find unblocked work
- `bd create "Title" --type task --priority 2` - Create issue
- `bd close <id>` - Complete work
- `bd sync` - Sync with git (run at session end)

For full workflow details: `bd prime`

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until a PR is created.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **CREATE PULL REQUEST** - This is MANDATORY:
   ```bash
   # Push current branch
   git push --set-upstream origin $(git branch --show-current)
   
   # Create PR (shows all commits since branching from main)
   gh pr create --title "type(scope): description" --body "Summary of changes..."
   
   # Verify PR created
   gh pr view
   ```
5. **WAIT FOR COPILOT CODE REVIEW** - After PR creation, wait 15 minutes for GitHub Copilot's automated code review to complete before proceeding
6. **MONITOR CI CHECKS** - Wait for all CI checks to complete:
   ```bash
   # Check CI status (wait until all checks pass or fail)
   gh pr checks <PR_NUMBER>
   ```
7. **ADDRESS ALL ISSUES** - Fix any failing CI checks or Copilot review comments:
   - If CI fails: investigate logs, fix issues, commit and push fixes
   - If Copilot suggests changes: review and implement reasonable suggestions
   - Iterate until all checks pass and reviews are addressed
8. **Clean up** - Clear stashes, mark beads in sync
   ```bash
   bd sync
   ```
9. **Verify** - PR shows "All checks have passed" and is merge-ready
10. **Hand off** - Provide context for next session with PR link

**CRITICAL RULES:**
- Work is NOT complete until PR is created on GitHub
- NEVER merge directly to main - ALWAYS use Pull Requests
- PR must show complete diff since branching point (not just latest commit)
- If PR creation fails, resolve and retry until it succeeds
- **MUST wait for Copilot code review (15 min) and address all feedback**
- **MUST wait for CI checks to complete and fix any failures**
- **Session ends ONLY when PR is merge-ready (green checks, reviews addressed)**

