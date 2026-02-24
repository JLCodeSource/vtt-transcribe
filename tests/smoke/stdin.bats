#!/usr/bin/env bats
# Smoke tests for stdin mode functionality

setup() {
    # Determine project root relative to test directory
    PROJECT_ROOT="${BATS_TEST_DIRNAME}/../.."
    
    # Load environment variables from .env if it exists and variables aren't already set
    if [[ -f "${PROJECT_ROOT}/.env" ]]; then
        set -a  # automatically export all variables
        source "${PROJECT_ROOT}/.env"
        set +a
    fi
    
    # Test input file paths
    TEST_AUDIO="${BATS_TEST_DIRNAME}/../hello_conversation.mp3"
    TEST_VIDEO="${BATS_TEST_DIRNAME}/../hello_conversation.mp4"
    DIARIZATION_IMAGE="${DIARIZATION_IMAGE:-vtt:diarization}"
    DIARIZATION_GPU_IMAGE="${DIARIZATION_GPU_IMAGE:-vtt:diarization-gpu}"
    SETUP_PYTHON_CLI="${SETUP_PYTHON_CLI:-1}"
    BUILD_BASE_IMAGE="${BUILD_BASE_IMAGE:-1}"
    BUILD_DIARIZATION_IMAGE="${BUILD_DIARIZATION_IMAGE:-1}"
    BUILD_DIARIZATION_GPU_IMAGE="${BUILD_DIARIZATION_GPU_IMAGE:-1}"
    
    # Skip if test audio doesn't exist
    if [[ ! -f "$TEST_AUDIO" ]]; then
        skip "Test audio file not found: $TEST_AUDIO"
    fi

    if [[ ! -f "$TEST_VIDEO" ]]; then
        skip "Test video file not found: $TEST_VIDEO"
    fi
    
    # Ensure venv is activated or vtt is available when Python CLI tests are enabled
    if [[ "$SETUP_PYTHON_CLI" == "1" ]] && [[ -f "${PROJECT_ROOT}/.venv/bin/vtt" ]]; then
        export PATH="${PROJECT_ROOT}/.venv/bin:$PATH"
    fi

    # Install vtt if not available (for package tests)
    if [[ "$SETUP_PYTHON_CLI" == "1" ]] && ! command -v vtt &> /dev/null; then
        echo "# Installing vtt package..." >&3
        cd "${PROJECT_ROOT}" && uv pip install -e . >&3 2>&1
        export PATH="${PROJECT_ROOT}/.venv/bin:$PATH"
    fi
    
    # Build Docker image if not available or force rebuild requested
    if [[ "$BUILD_BASE_IMAGE" == "1" ]] && ([[ "$FORCE_DOCKER_REBUILD" == "1" ]] || ! docker image inspect vtt:latest &> /dev/null); then
        echo "# Building vtt:latest Docker image..." >&3
        BUILD_FLAGS=""
        if [[ "$DOCKER_NO_CACHE" == "1" ]]; then
            BUILD_FLAGS="--no-cache"
        fi
        cd "${PROJECT_ROOT}" && docker build $BUILD_FLAGS -t vtt:latest . >&3 2>&1
    fi
    
    # Build Docker diarization image if not available or force rebuild requested
    if [[ "$BUILD_DIARIZATION_IMAGE" == "1" ]] && ([[ "$FORCE_DOCKER_REBUILD" == "1" ]] || ! docker image inspect "$DIARIZATION_IMAGE" &> /dev/null); then
        echo "# Building $DIARIZATION_IMAGE Docker image..." >&3
        BUILD_FLAGS=""
        if [[ "$DOCKER_NO_CACHE" == "1" ]]; then
            BUILD_FLAGS="--no-cache"
        fi
        cd "${PROJECT_ROOT}" && docker build $BUILD_FLAGS -f Dockerfile.diarization -t "$DIARIZATION_IMAGE" . >&3 2>&1
    fi

    # Build Docker diarization GPU image if not available or force rebuild requested
    if [[ "$BUILD_DIARIZATION_GPU_IMAGE" == "1" ]] && ([[ "$FORCE_DOCKER_REBUILD" == "1" ]] || ! docker image inspect "$DIARIZATION_GPU_IMAGE" &> /dev/null); then
        echo "# Building $DIARIZATION_GPU_IMAGE Docker image..." >&3
        BUILD_FLAGS=""
        if [[ "$DOCKER_NO_CACHE" == "1" ]]; then
            BUILD_FLAGS="--no-cache"
        fi
        cd "${PROJECT_ROOT}" && docker build $BUILD_FLAGS -f Dockerfile.diarization-gpu -t "$DIARIZATION_GPU_IMAGE" . >&3 2>&1
    fi
}

@test "stdin mode: uv run transcribes from stdin" {
    # Skip if OPENAI_API_KEY not set
    if [[ -z "$OPENAI_API_KEY" ]]; then
        skip "OPENAI_API_KEY not set (set in environment or .env file)"
    fi
    
    run bash -c "export OPENAI_API_KEY='$OPENAI_API_KEY' && cd '$PROJECT_ROOT' && cat '$TEST_AUDIO' | uv run vtt_transcribe/main.py"
    
    [ "$status" -eq 0 ]
    [[ "$output" =~ "hello world" ]] || [[ "$output" =~ "Hello world" ]]
}

@test "stdin mode: installed package transcribes from stdin" {
    # Skip if OPENAI_API_KEY not set
    if [[ -z "$OPENAI_API_KEY" ]]; then
        skip "OPENAI_API_KEY not set (set in environment or .env file)"
    fi
    
    run bash -c "export OPENAI_API_KEY='$OPENAI_API_KEY' && cat '$TEST_AUDIO' | vtt"
    
    # Debug output on failure
    if [ "$status" -ne 0 ]; then
        echo "Exit status: $status"
        echo "Output: $output"
    fi
    
    [ "$status" -eq 0 ]
    [[ "$output" =~ "hello world" ]] || [[ "$output" =~ "Hello world" ]]
}

@test "stdin mode: docker transcribes from stdin with env var" {
    # Skip if docker not available
    if ! command -v docker &> /dev/null; then
        skip "docker not available"
    fi
    
    # Skip if OPENAI_API_KEY not set
    if [[ -z "$OPENAI_API_KEY" ]]; then
        skip "OPENAI_API_KEY not set (set in environment or .env file)"
    fi
    
    run bash -c "cat '$TEST_AUDIO' | docker run -i -e OPENAI_API_KEY=\"\$OPENAI_API_KEY\" vtt:latest"
    
    [ "$status" -eq 0 ]
    [[ "$output" =~ "hello world" ]] || [[ "$output" =~ "Hello world" ]]
}

@test "stdin mode: docker transcribes with output redirect" {
    # Skip if docker not available
    if ! command -v docker &> /dev/null; then
        skip "docker not available"
    fi
    
    # Skip if OPENAI_API_KEY not set
    if [[ -z "$OPENAI_API_KEY" ]]; then
        skip "OPENAI_API_KEY not set (set in environment or .env file)"
    fi
    
    # Create temp file for output
    TEMP_TRANSCRIPT=$(mktemp)
    
    # Run with output redirect
    cat "$TEST_AUDIO" | docker run -i -e OPENAI_API_KEY="$OPENAI_API_KEY" vtt:latest > "$TEMP_TRANSCRIPT"
    
    # Check output file
    [[ -s "$TEMP_TRANSCRIPT" ]]
    grep -qi "hello world" "$TEMP_TRANSCRIPT"
    
    # Cleanup
    rm -f "$TEMP_TRANSCRIPT"
}

@test "stdin mode: docker diarization (HF-only) with env vars" {
    # Skip if docker not available
    if ! command -v docker &> /dev/null; then
        skip "docker not available"
    fi
    
    # Skip if HF_TOKEN not set (needed for diarization)
    if [[ -z "$HF_TOKEN" ]]; then
        skip "HF_TOKEN not set (set in environment or .env file)"
    fi

    if ! docker image inspect "$DIARIZATION_IMAGE" &> /dev/null; then
        skip "Diarization image not found: $DIARIZATION_IMAGE"
    fi
    
    run bash -c "cat '$TEST_AUDIO' | docker run -i -e HF_TOKEN=\"\$HF_TOKEN\" '$DIARIZATION_IMAGE' --diarize-only --no-review-speakers --hf-token \"\$HF_TOKEN\""
    
    [ "$status" -eq 0 ]
    [[ "$output" =~ "SPEAKER" ]]
}

@test "stdin mode: docker diarization transcribes mp4 from stdin" {
    # Skip if docker not available
    if ! command -v docker &> /dev/null; then
        skip "docker not available"
    fi

    # Skip if HF_TOKEN not set (needed for diarization)
    if [[ -z "$HF_TOKEN" ]]; then
        skip "HF_TOKEN not set (set in environment or .env file)"
    fi

    if ! docker image inspect "$DIARIZATION_IMAGE" &> /dev/null; then
        skip "Diarization image not found: $DIARIZATION_IMAGE"
    fi

    run bash -c "cat '$TEST_VIDEO' | docker run -i -e HF_TOKEN=\"\$HF_TOKEN\" '$DIARIZATION_IMAGE' --diarize-only --no-review-speakers --hf-token \"\$HF_TOKEN\""

    [ "$status" -eq 0 ]
    [[ "$output" =~ "SPEAKER" ]]
}

@test "stdin mode: docker diarization-gpu transcribes mp4 from stdin" {
    # Skip if docker not available
    if ! command -v docker &> /dev/null; then
        skip "docker not available"
    fi

    # Skip if HF_TOKEN not set (needed for diarization)
    if [[ -z "$HF_TOKEN" ]]; then
        skip "HF_TOKEN not set (set in environment or .env file)"
    fi

    if ! docker image inspect "$DIARIZATION_GPU_IMAGE" &> /dev/null; then
        skip "Diarization GPU image not found: $DIARIZATION_GPU_IMAGE"
    fi

    run bash -c "cat '$TEST_VIDEO' | docker run -i -e HF_TOKEN=\"\$HF_TOKEN\" '$DIARIZATION_GPU_IMAGE' --diarize-only --no-review-speakers --hf-token \"\$HF_TOKEN\""

    [ "$status" -eq 0 ]
    [[ "$output" =~ "SPEAKER" ]]
}
