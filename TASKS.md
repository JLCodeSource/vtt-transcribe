# VTT-Transcribe PyPI Publishing Implementation Tasks

## T000: Project Setup & Infrastructure
- [x] T000_000: Create Dockerfile with GitHub CLI (gh) and uv
- [x] T000_001: Setup copilot worktree in .copilot-worktrees/ (gitignored but git-tracked)
- [ ] T000_002: Verify git worktree workflow (commit, push, PR from worktree)

## T005: GitHub CLI & Task Management Integration
- [x] T005_000: Authenticate gh CLI in container (gh auth login)
- [x] T005_001: Verify gh CLI can access vtt-transcribe repository
- [ ] T005_002: Create GitHub issues for all tasks in this file
- [ ] T005_003: Add issues to vtt-transcribe GitHub project board
- [ ] T005_004: Create automation script to sync TASKS.md ↔ GitHub issues
- [ ] T005_005: Setup task status tracking (open/in-progress/done)
- [ ] T005_006: Link tasks to commits (reference task numbers in commit messages)
- [ ] T005_007: Create script to auto-close issues when tasks marked done

## T100: Package Naming & Structure
- [ ] T100_000: Update pyproject.toml project name to "vtt-transcribe"
- [ ] T100_001: Add Hatch build system to pyproject.toml
- [ ] T100_002: Update entry point to use "vtt_transcribe.main:main"
- [ ] T100_003: Rename source directory: vtt/ → vtt_transcribe/
- [ ] T100_004: Update all internal imports from "vtt." to "vtt_transcribe."
- [ ] T100_005: Update test imports from "vtt." to "vtt_transcribe."
- [ ] T100_006: Search/verify no remaining "from vtt." or "import vtt." references

## T200: Build System Configuration
- [ ] T200_000: Add pyproject.toml [tool.hatch] configuration
- [ ] T200_001: Configure package discovery (include vtt_transcribe/)
- [ ] T200_002: Test local build with: uv run python -m build
- [ ] T200_003: Verify sdist and wheel in dist/ contain correct package name
- [ ] T200_004: Test local install: pip install dist/*.whl
- [ ] T200_005: Verify CLI works: vtt --help and uv run vtt --help

## T300: GitHub Actions Workflow
- [ ] T300_000: Update .github/workflows/publish.yml to use Hatch/build
- [ ] T300_001: Configure OIDC permissions for PyPI publishing
- [ ] T300_002: Add environment: pypi to publish job
- [ ] T300_003: Test workflow with workflow_dispatch trigger (dry-run)
- [ ] T300_004: Verify package_dir: dist in pypa/gh-action-pypi-publish

## T400: Testing & Validation
- [ ] T400_000: Run existing test suite: uv run pytest
- [ ] T400_001: Add test for CLI entry point (import and execute)
- [ ] T400_002: Add test for package import: import vtt_transcribe
- [ ] T400_003: Run type checking: uv run mypy vtt_transcribe/
- [ ] T400_004: Run linting: uv run ruff check
- [ ] T400_005: Update pre-commit hooks for new package name (vtt_transcribe)
- [ ] T400_006: Verify pre-commit hooks pass
- [ ] T400_007: Test that vtt command works after local install

## T500: Documentation & Release Prep
- [ ] T500_000: Update README.md installation: pip install vtt-transcribe
- [ ] T500_001: Update README.md usage examples (vtt, uv run vtt)
- [ ] T500_002: Update CHANGELOG.md for v0.3.0b1 release
- [ ] T500_003: Update pyproject.toml version to 0.3.0b1
- [ ] T500_004: Add PyPI classifiers and project URLs to pyproject.toml
- [ ] T500_005: Review and update project description/keywords

## T600: PyPI Configuration
- [ ] T600_000: Verify PyPI project "vtt-transcribe" is registered
- [ ] T600_001: Configure TestPyPI for testing releases
- [ ] T600_002: Setup GitHub repository environment "pypi" with protection rules
- [ ] T600_003: Test publish to TestPyPI first
- [ ] T600_004: Verify TestPyPI install: pip install -i https://test.pypi.org/simple/ vtt-transcribe

## T700: Release Workflow
- [ ] T700_000: Create release checklist document
- [ ] T700_001: Tag version: git tag v0.3.0b1
- [ ] T700_002: Push tags: git push origin v0.3.0b1
- [ ] T700_003: Create GitHub release (draft=false triggers publish workflow)
- [ ] T700_004: Monitor GitHub Actions publish job
- [ ] T700_005: Verify package on PyPI: https://pypi.org/project/vtt-transcribe/

## T800: Post-Release Validation
- [ ] T800_000: Test installation from PyPI: pip install vtt-transcribe
- [ ] T800_001: Verify CLI works after PyPI install: vtt --help
- [ ] T800_002: Test uv run: uv run vtt --help (should download from PyPI)
- [ ] T800_003: Test import in fresh environment: python -c "import vtt_transcribe"
- [ ] T800_004: Check package metadata on PyPI looks correct

## T900: Merge & Cleanup
- [ ] T900_000: Commit all changes in worktree with descriptive messages
- [ ] T900_001: Push worktree branch to remote
- [ ] T900_002: Merge worktree branch to packaging/v0.3.0b1
- [ ] T900_003: Create PR from packaging/v0.3.0b1 to main
- [ ] T900_004: Review and merge PR
- [ ] T900_005: Delete merged worktree branch
- [ ] T900_006: Prune old worktrees: git worktree prune
- [ ] T900_007: Update project documentation with publishing workflow
- [ ] T900_008: Close all completed GitHub issues
- [ ] T900_009: Archive completed tasks in GitHub project

---

## Notes
- Tasks must be completed in order within each section (T005s, then T100s, then T200s, etc.)
- Complete T005 (GitHub integration) before starting T100 (package rename)
- Some tasks within a section can be done in parallel
- Run tests after each major section (T100, T200, T400)
- Commit frequently with descriptive messages referencing task numbers (e.g., "T100_003: Rename vtt/ to vtt_transcribe/")
- Push to remote worktree branch regularly for backup
- Update GitHub issues as tasks are completed
- Multi-platform testing (Linux/Mac/Windows) and multi-Python versions deferred to v0.4.0
- All tasks assigned to @copilot
