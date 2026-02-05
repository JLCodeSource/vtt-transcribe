# cibuildwheel Implementation Plan

**Epic:** vtt-transcribe-awg - CI/CD: cibuildwheel wheel building and PyPI publishing  
**Status:** Planning Phase  
**Date:** 2026-02-05

## Overview

This plan outlines the implementation strategy for adding cibuildwheel-based wheel building to vtt-transcribe. The goal is to produce platform-specific binary wheels for Python 3.10-3.14 across Linux, macOS, and Windows, with special handling for the optional diarization feature.

## Current State

### Existing Infrastructure
- **Build System:** Hatchling-based pure Python package
- **Publishing:** OIDC-authenticated PyPI publishing via GitHub Actions ([publish.yml](../.github/workflows/publish.yml))
- **CI:** Standard pytest/lint checks on Python 3.13 ([ci.yml](../.github/workflows/ci.yml))
- **Docker:** Dual-image strategy (base + diarization) with layer caching ([docker-build-test.yml](../.github/workflows/docker-build-test.yml))
- **Python Support:** Python >=3.10 in pyproject.toml
- **Diarization:** Optional extra with torch==2.8.0 (pinned due to 2.10+ breaking changes)

### Current Limitations
1. **No binary wheels:** Only sdist distribution, leading to slow installs on some platforms
2. **Python version gating:** Torch wheels only exist through 3.13 (Python 3.14 must be core-only)
3. **CI costs:** Diarization builds are expensive (PyTorch + pyannote)
4. **Platform support:** Need to validate wheel builds across Linux/macOS/Windows

## Key Challenges

### 1. Python Version Matrix
- **Target:** Python 3.10, 3.11, 3.12, 3.13, 3.14
- **Core package:** All versions (3.10-3.14)
- **Diarization extra:** Only 3.10-3.13 (torch availability constraint)
- **Python 3.14:** Core only, no torch/pyannote

### 2. Build Matrix Complexity
```
Platform     Architecture    Python Versions    Diarization Support
-----------  --------------  -----------------  --------------------
Linux        x86_64, arm64   3.10-3.14          3.10-3.13 only
macOS        x86_64, arm64   3.10-3.14          3.10-3.13 only
Windows      x86_64          3.10-3.14          3.10-3.13 only
```

### 3. CI Cost Control
- Diarization builds are heavy (torch downloads ~800MB, pyannote models ~300MB)
- Need to gate diarization jobs to main branch only
- Skip diarization builds on PRs and feature branches
- Use build caching effectively

### 4. Dependency Resolution
- Core dependencies are pure Python (moviepy, openai, python-dotenv)
- Diarization adds binary dependencies (torch, pyannote)
- Need conditional installation in cibuildwheel environment

## Implementation Plan

### Phase 1: Prerequisites & Documentation (P2)
**Task:** vtt-transcribe-ra4 - docs: document CI & nox changes and add cibuildwheel plan

**Actions:**
1. ✅ Create this planning document (CIBUILDWHEEL_PLAN.md)
2. ✅ Update pyproject.toml:
  - Relax `requires-python = ">=3.10"`
  - Update classifiers to include all Python versions
3. ✅ Add nox configuration for multi-version testing:
  - Tests with diarization extras on 3.10-3.13
  - Core-only tests on 3.14 (skip diarization)
  - Lint on 3.10
4. Document build matrix and gating rules
5. Add CI workflow documentation

**Deliverables:**
- `docs/CIBUILDWHEEL_PLAN.md` (this file)
- `docs/CI_WORKFLOWS.md` (workflow reference)
- ✅ `noxfile.py` (multi-Python testing)
- ✅ Updated `pyproject.toml` with relaxed Python requirements

### Phase 2: Docker CI Optimization (P2)
**Task:** vtt-transcribe-qac - CI: Update docker-build-test-diarization to run only on main (skip PRs)

**Current Behavior:**
```yaml
# docker-build-test.yml
docker-build-test-diarization:
  if: github.event_name != 'pull_request'  # Already present!
```

**Actions:**
1. ✅ Verify current gating is correct (it is!)
2. Add additional check to ensure it only runs on main branch:
   ```yaml
   if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
   ```
3. Update job documentation/comments to clarify the gating
4. Consider adding a manual workflow_dispatch trigger for testing

**Rationale:**
- Diarization Docker builds are expensive (~5GB image, torch downloads)
- PRs don't need diarization validation (covered by unit tests)
- Main branch builds provide sufficient coverage for releases

### Phase 3: Python 3.14 Core-Only Gating (P2)
**Task:** vtt-transcribe-djw - CI: Ensure Python 3.14 builds only core (no diarization)

**Problem:**
- torch 2.8.0 doesn't have wheels for Python 3.14
- Installing diarization extras on 3.14 will fail or require source builds
- Need to explicitly test and build 3.14 without diarization

**Actions:**
1. Update pyproject.toml to document Python 3.14 limitation:
   ```toml
   [project.optional-dependencies]
   diarization = [
       "pyannote.audio>=3.1.0",
       "torch==2.8.0; python_version<'3.14'",  # Add version constraint
   ]
   ```
2. Add nox session that tests 3.14 without diarization extras
3. Configure cibuildwheel to skip diarization for 3.14:
   ```yaml
   CIBW_TEST_EXTRAS: "diarization"  # Default
   CIBW_TEST_EXTRAS_LINUX: "diarization"
   CIBW_TEST_EXTRAS_MACOS: "diarization"
   CIBW_TEST_EXTRAS_WINDOWS: "diarization"
   # Override for 3.14
   CIBW_TEST_EXTRAS_PY314: ""  # No extras for 3.14
   ```
4. Add clear documentation in README about Python 3.14 limitations

**Testing:**
```bash
# Test core on 3.14 (should work)
python3.14 -m venv test-env
source test-env/bin/activate
pip install vtt-transcribe
vtt --version  # Should work

# Test diarization on 3.14 (should fail gracefully with clear error)
pip install vtt-transcribe[diarization]  # Should skip torch or show clear error
```

### Phase 4: cibuildwheel Workflow Implementation (P1)
**Task:** vtt-transcribe-mfp - CI: Add cibuildwheel workflow for wheel builds (core + diarization gating)

**Updated Architecture:**
```yaml
name: Build Wheels

on:
  push:
    tags: ['v*', 'v*b*']  # Include pre-release tags
  release:
    types: [published]
  workflow_dispatch:

jobs:
  build-core-wheels:
    # Builds wheels with NO extras (pure Python, all platforms, all versions)
    # Fast, cheap, always runs

  build-diarization-wheels:
    # Builds wheels WITH diarization extras (binary deps, expensive)
    # Only runs on main branch, gated to Python 3.10-3.13
    # Requires torch/pyannote downloads

  publish-wheels:
    needs: [build-core-wheels, build-diarization-wheels]
    # Publishes all wheels to PyPI
```

**Core Wheels Job:**
```yaml
build-core-wheels:
  name: Build core wheels on ${{ matrix.os }}
  runs-on: ${{ matrix.os }}
  strategy:
    matrix:
      os: [ubuntu-latest, windows-latest, macos-13, macos-14]  # Intel + ARM

  steps:
    - uses: actions/checkout@v4
    
    - uses: pypa/cibuildwheel@v2.21
      env:
        CIBW_BUILD: "cp310-* cp311-* cp312-* cp313-* cp314-*"
        CIBW_ARCHS_LINUX: "x86_64 aarch64"
        CIBW_ARCHS_MACOS: "x86_64 arm64"
        CIBW_ARCHS_WINDOWS: "AMD64"
        CIBW_TEST_COMMAND: "nox -s tests_core"
        CIBW_TEST_REQUIRES: "nox"
        # Include musllinux builds
        CIBW_SKIP: ""

    - uses: actions/upload-artifact@v4
      with:
        name: wheels-core-${{ matrix.os }}
        path: ./wheelhouse/*.whl
```

**Diarization Wheels Job:**
```yaml
build-diarization-wheels:
  name: Build diarization wheels on ${{ matrix.os }}
  runs-on: ${{ matrix.os }}
  if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')
  strategy:
    matrix:
      os: [ubuntu-latest]  # Start with Linux only, expand later
      python: ["3.10", "3.11", "3.12", "3.13"]  # No 3.14!

  steps:
    - uses: actions/checkout@v4
    
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python }}
    
    - name: Install ffmpeg (required for tests)
      run: |
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    
    - uses: pypa/cibuildwheel@v2.21
      env:
        CIBW_BUILD: "cp${{ matrix.python }}-*"
        CIBW_ARCHS_LINUX: "x86_64"
        CIBW_TEST_EXTRAS: "diarization,dev"
        CIBW_TEST_COMMAND: "nox -s tests"
        CIBW_BEFORE_TEST: "pip install torch==2.8.0 pyannote.audio>=3.1.0"
        CIBW_TEST_REQUIRES: "nox"
        # Cache torch downloads
        CIBW_ENVIRONMENT: "PIP_CACHE_DIR=/tmp/pip-cache"
    
    - uses: actions/upload-artifact@v4
      with:
        name: wheels-diarization-py${{ matrix.python }}-${{ matrix.os }}
        path: ./wheelhouse/*.whl
```

**Publish Job:**
```yaml
publish-wheels:
  name: Publish wheels to PyPI
  needs: [build-core-wheels, build-diarization-wheels]
  runs-on: ubuntu-latest
  if: github.event_name == 'release' && github.event.action == 'published'
  environment: pypi
  permissions:
    id-token: write
    contents: read

  steps:
    - uses: actions/download-artifact@v4
      with:
        pattern: wheels-*
        path: dist
        merge-multiple: true
    
    - name: List wheels
      run: ls -lh dist/
    
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        packages-dir: dist/
```

**Key Updates:**
1. **Pre-Release Testing:** Added `v*b*` tags to triggers for pre-release builds.
2. **musllinux Support:** Removed `-musllinux` skip from `CIBW_SKIP`.
3. **Nox Integration:** Replaced `CIBW_TEST_COMMAND` with Nox-based test commands.
4. **Workflow Alignment:** Ensured seamless integration with `publish.yml` and `publish-testpypi.yml`.

### Phase 5: Testing & Validation

**Test Plan:**
1. **Local Testing:**
   ```bash
   # Install cibuildwheel
   pip install cibuildwheel
   
   # Build locally (Linux)
   cibuildwheel --platform linux --archs x86_64
   
   # Test wheel installation
   pip install dist/*.whl
   vtt --version
   ```

2. **TestPyPI Validation:**
   - Trigger workflow with workflow_dispatch
   - Build all wheels
   - Upload to TestPyPI
   - Install and test: `pip install -i https://test.pypi.org/simple/ vtt-transcribe`

3. **Multi-Platform Testing:**
   - Use GitHub Actions matrix to test all platforms
   - Verify wheel naming follows PEP standards
   - Check wheel sizes (core should be small, diarization larger)

4. **Version-Specific Tests:**
   - Test Python 3.10-3.13 with diarization
   - Test Python 3.14 without diarization
   - Verify torch installs correctly on 3.10-3.13
   - Verify torch is NOT required on 3.14

### Phase 6: Documentation Updates

**README Updates:**
```markdown
## Installation

### Core Package (All Python versions)
```bash
pip install vtt-transcribe  # Python 3.10-3.14
```

### With Speaker Diarization (Python 3.10-3.13 only)
```bash
pip install vtt-transcribe[diarization]  # Requires Python 3.10-3.13
```

**Note:** Diarization features require PyTorch, which currently supports Python 3.10-3.13. 
Python 3.14 users can install the core package for transcription without speaker identification.
```

**CHANGELOG Entry:**
```markdown
## [0.3.1] - TBD

### Added
- Binary wheel distributions for faster installation across platforms
- Multi-platform support (Linux x86_64/arm64, macOS Intel/ARM, Windows x64)
- Python 3.10-3.14 support (diarization available on 3.10-3.13)

### Changed
- Relaxed Python requirement from >=3.13 to >=3.10
- Added nox for multi-version testing
- Optimized CI workflows to reduce build times and costs
```

## Implementation Order

### Phase 0: Planning (✅ Complete)
- [x] Create epic: vtt-transcribe-awg
- [x] Link existing tasks to epic
- [x] Document implementation plan (this file)

### Phase 1: Prerequisites (2-3 hours)
**Tasks:** vtt-transcribe-ra4

1. Update pyproject.toml (requires-python, classifiers, torch constraint)
2. Create noxfile.py for multi-Python testing
3. Document CI workflows
4. Test nox sessions locally

### Phase 2: Docker Optimization (30 min)
**Tasks:** vtt-transcribe-qac

1. Update docker-build-test.yml with stricter gating
2. Add workflow comments/documentation
3. Test workflow_dispatch trigger

### Phase 3: Python 3.14 Gating (1 hour)
**Tasks:** vtt-transcribe-djw

1. Add torch version constraint in pyproject.toml
2. Test 3.14 installation (core only)
3. Verify error messages are clear
4. Update README with Python version notes

### Phase 4: cibuildwheel Implementation (4-6 hours)
**Tasks:** vtt-transcribe-mfp

1. Create `.github/workflows/build-wheels.yml`
2. Configure core wheels job (all platforms, all versions)
3. Configure diarization wheels job (gated, 3.10-3.13 only)
4. Set up artifact collection and publishing
5. Add workflow_dispatch for testing
6. Test on TestPyPI

### Phase 5: Testing & Validation (2-3 hours)
1. Run workflow_dispatch to build all wheels
2. Download and test wheels locally on multiple platforms
3. Verify wheel sizes and contents
4. Test installation from TestPyPI
5. Run full test suite with installed wheels

### Phase 6: Documentation & Release (1-2 hours)
1. Update README with installation instructions
2. Update CHANGELOG
3. Document known limitations
4. Create release with tag
5. Monitor PyPI publish
6. Verify wheels are available on PyPI

## Success Criteria

- [ ] Wheels available for Python 3.10-3.14 on PyPI
- [ ] Core wheels available for all platforms (Linux, macOS, Windows)
- [ ] Diarization works on Python 3.10-3.13
- [ ] Python 3.14 installs core successfully (no diarization)
- [ ] Installation is fast (no source builds required)
- [ ] CI costs controlled through selective diarization builds
- [ ] Clear documentation of Python version support
- [ ] All tests pass on all platforms

## Risks & Mitigations

### Risk 1: Platform-Specific Build Failures
**Mitigation:** Start with Linux only, expand incrementally to macOS and Windows

### Risk 2: Torch Download Timeouts
**Mitigation:** Use pip caching, increase timeout limits, add retry logic

### Risk 3: Wheel Size Explosion
**Mitigation:** Keep torch as optional dependency, separate core/diarization builds

### Risk 4: Python 3.14 Compatibility Issues
**Mitigation:** Test extensively on 3.14, document limitations clearly

### Risk 5: CI Cost Overruns
**Mitigation:** Gate diarization builds to main only, use workflow_dispatch for testing

## Open Questions

1. **ARM64 Linux:** Should we build arm64 Linux wheels? (Answer: Yes, for Raspberry Pi and cloud ARM instances)
2. **musllinux:** Should we support musl-based Linux? (Answer: Defer to later, glibc first)
3. **PyPy:** Should we support PyPy? (Answer: No, focus on CPython)
4. **Nightly Builds:** Should we build nightly wheels for testing? (Answer: No, use workflow_dispatch)

## References

- [cibuildwheel Documentation](https://cibuildwheel.pypa.io/)
- [PyPA Wheel Naming Convention](https://packaging.python.org/en/latest/specifications/binary-distribution-format/)
- [GitHub Actions: cibuildwheel Examples](https://github.com/pypa/cibuildwheel/tree/main/examples)
- [Torch Compatibility Matrix](https://pytorch.org/)
- [pyannote.audio Documentation](https://github.com/pyannote/pyannote-audio)

## Related Issues

- Epic: vtt-transcribe-awg (this epic)
- vtt-transcribe-mfp: CI: Add cibuildwheel workflow (P1)
- vtt-transcribe-ra4: docs: document CI & nox changes (P2)
- vtt-transcribe-qac: CI: Update docker-build-test-diarization (P2)
- vtt-transcribe-djw: CI: Ensure Python 3.14 builds only core (P2)
