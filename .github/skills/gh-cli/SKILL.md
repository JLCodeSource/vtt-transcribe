---
name: gh-cli
description: GitHub CLI reference for common repository, issue, PR, and workflow operations.
tools: ["terminal"]
---

# GitHub CLI (gh)

Use `gh` for all GitHub operations instead of manual web interactions.

## Common Commands

### Issues
```bash
gh issue list                           # List issues
gh issue view 123                       # View issue details
gh issue create --title "Bug" --body "Description"
gh issue close 123 --comment "Fixed"
gh issue edit 123 --add-label bug
```

### Pull Requests
```bash
gh pr list                              # List PRs
gh pr view 123                          # View PR
gh pr create --title "Feature" --body "Description"
gh pr checkout 123                      # Checkout PR branch
gh pr merge 123 --squash                # Squash merge
gh pr review 123 --approve              # Approve PR
```

### Repositories
```bash
gh repo view                            # View current repo
gh repo view owner/repo                 # View specific repo
gh repo clone owner/repo                # Clone repo
gh repo fork owner/repo                 # Fork repo
```

### Workflows
```bash
gh workflow list                        # List workflows
gh workflow run ci.yml                  # Trigger workflow
gh run list                             # List workflow runs
gh run view 123                         # View run details
gh run watch                            # Watch latest run
```

## JSON Output

Use `--json` for programmatic access:
```bash
gh issue list --json number,title,state
gh pr list --json number,title,author --jq '.[] | select(.author.login == "me")'
```

## Authentication

```bash
gh auth login                           # Login interactively
gh auth status                          # Check auth status
gh auth token                           # Get auth token
```

## References
- Manual: https://cli.github.com/manual/
- Docs: https://docs.github.com/en/github-cli
