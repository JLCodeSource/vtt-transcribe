# Comprehensive Logging Implementation Plan

## Overview
Add structured logging across all vtt-transcribe modules to improve debugging, monitoring, and production support.

## Modules to Update

### 1. CLI & Validation (main.py, cli.py)
- Log CLI startup and argument parsing
- Log validation errors with context
- Log mode selection (stdin, diarize-only, etc.)
- Log API key source (arg vs env)

### 2. Audio Management (audio_manager.py, audio_chunker.py)
- Log audio extraction start/complete with timing
- Log chunk creation with parameters
- Log file operations (create, delete)
- Log audio file metadata (duration, size, format)

### 3. Transcription (transcriber.py)
- Log transcription start/complete with timing
- Log chunk processing progress
- Log API calls and responses (sanitized)
- Log file operations and cleanup

### 4. Diarization (diarization.py) - PARTIALLY DONE
- Enhance existing logging
- Add speaker segment details
- Log model loading and device info

### 5. Translation (translator.py)
- Log translation start/complete
- Log language detection
- Log batch translation operations
- Log API interactions

### 6. Handlers (handlers.py)
- Log workflow orchestration
- Log file I/O operations
- Log speaker review interactions

### 7. API Routes (api/routes/*.py)
- Log HTTP requests with sanitized data
- Log job lifecycle events
- Log WebSocket connections
- Log error responses

## Logging Patterns

### Standard Entry/Exit
```python
logger = get_logger(__name__)

def some_operation(param: str) -> Result:
    logger.info("Starting operation", extra={"param": param})
    try:
        # work
        logger.info("Operation complete", extra={"result_size": len(result)})
        return result
    except Exception as e:
        logger.error("Operation failed", extra={"error": str(e)}, exc_info=True)
        raise
```

### Timing/Performance
```python
import time
start_time = time.time()
# operation
duration = time.time() - start_time
logger.info("Operation timing", extra={"duration_seconds": duration, "operation": "transcribe"})
```

### Context Tracking
```python
logger.info("Processing job", extra={
    "job_id": job_id,
    "filename": filename,
    "file_size_mb": file_size / 1024 / 1024,
    "duration_seconds": duration
})
```

## Testing Strategy
- Test log output in dev mode (human-readable)
- Test log output in production mode (JSON)
- Test context propagation
- Test structured fields
- Test error logging with exc_info
