# Logging Guide

This guide explains how to use the comprehensive logging infrastructure in vtt-transcribe.

## Overview

vtt-transcribe includes a robust, structured logging system that provides:

- **Environment-based configuration** (development vs production)
- **Structured logging** with JSON output for production
- **Operation context tracking** with correlation IDs
- **Multiple output destinations** (console and file)
- **Log rotation** for long-running applications
- **Performance and timing metrics**

## Quick Start

### Basic Usage

```python
from vtt_transcribe.logging_config import get_logger

logger = get_logger(__name__)

# Simple logging
logger.info("Starting transcription")
logger.error("Failed to process file", exc_info=True)

# Structured logging with context
logger.info("Processing complete", extra={
    "duration_seconds": 45.2,
    "file_size_mb": 12.5,
    "status": "success"
})
```

### Operation Context Tracking

Use operation contexts to track requests and operations across module boundaries:

```python
from vtt_transcribe.logging_config import get_logger, operation_context

logger = get_logger(__name__)

def transcribe_file(filename: str, api_key: str) -> str:
    # Create operation context with correlation ID
    with operation_context("transcribe_audio", filename=filename) as operation_id:
        logger.info("Starting transcription")  # Automatically includes operation_id and filename
        
        # All logs within this context include the correlation ID
        result = _do_transcription(filename, api_key)
        
        logger.info("Transcription complete", extra={"result_length": len(result)})
        return result

def _do_transcription(filename: str, api_key: str) -> str:
    # Even in different functions, logs include the operation context
    logger.info("Calling Whisper API")  # Includes operation_id and filename automatically
    # ... implementation ...
    return "transcription result"
```

### File Logging with Rotation

```python
from vtt_transcribe.logging_config import setup_logging

# Setup logging with file output and rotation
logger = setup_logging(
    dev_mode=False,  # Use JSON format
    log_file="/var/log/vtt-transcribe/app.log",
    enable_rotation=True,
    max_bytes=10 * 1024 * 1024,  # 10MB files
    backup_count=5  # Keep 5 rotated files
)

logger.info("Application started")
```

## Configuration

### Environment-Based Setup

The logging system automatically detects the environment:

- **Development** (`VTT_ENV=development` or default): Human-readable console output, DEBUG level
- **Production** (`VTT_ENV=production`): JSON console output, INFO level

```python
# Automatic environment detection
logger = setup_logging()

# Manual override
logger = setup_logging(dev_mode=False)  # Force production mode
logger = setup_logging(dev_mode=True)   # Force development mode
```

### Multiple Output Destinations

```python
# Console only (default)
logger = setup_logging()

# Console + file
logger = setup_logging(log_file="/path/to/app.log")

# Console (stderr) + file (useful for CLI tools)
logger = setup_logging(use_stderr=True, log_file="/path/to/app.log")
```

### Log Rotation Configuration

```python
logger = setup_logging(
    log_file="/path/to/app.log",
    enable_rotation=True,        # Enable rotation (default)
    max_bytes=50 * 1024 * 1024, # 50MB per file
    backup_count=10             # Keep 10 old files
)

# Disable rotation for simple file logging
logger = setup_logging(
    log_file="/path/to/app.log",
    enable_rotation=False
)
```

## Log Formats

### Development Format (Human-Readable)

```
2026-02-10 15:30:45 - vtt_transcribe.transcriber - INFO - Starting transcription
2026-02-10 15:30:47 - vtt_transcribe.transcriber - ERROR - API call failed
```

### Production Format (JSON)

```json
{
    "timestamp": "2026-02-10T15:30:45",
    "level": "INFO",
    "logger": "vtt_transcribe.transcriber",
    "message": "Starting transcription",
    "operation_id": "123e4567-e89b-12d3-a456-426614174000",
    "operation_name": "transcribe_audio",
    "filename": "audio.mp3",
    "file_size_mb": 12.5
}
```

## Operation Context Examples

### CLI Operations

```python
from vtt_transcribe.logging_config import operation_context, get_logger

logger = get_logger(__name__)

def main():
    """Main CLI entry point."""
    args = parse_args()
    
    # Track the entire CLI operation
    with operation_context("cli_transcription", 
                          input_file=args.input,
                          output_format=args.format) as op_id:
        
        logger.info("CLI started", extra={"args_count": len(sys.argv)})
        
        try:
            result = transcribe_file(args.input, args.api_key)
            logger.info("CLI completed successfully")
            return 0
        except Exception as e:
            logger.error("CLI failed", exc_info=True)
            return 1
```

### API Request Tracking

```python
from fastapi import Request
from vtt_transcribe.logging_config import operation_context, get_logger

logger = get_logger(__name__)

@app.post("/transcribe")
async def transcribe_endpoint(request: Request, file: UploadFile):
    """API endpoint with request tracking."""
    
    # Generate correlation ID for this request
    with operation_context("api_transcription",
                          client_ip=request.client.host,
                          filename=file.filename,
                          content_type=file.content_type) as request_id:
        
        logger.info("API request received")
        
        try:
            # Process the transcription
            result = await process_transcription(file)
            
            logger.info("API request completed", extra={
                "response_size": len(result),
                "processing_time": time.time() - start_time
            })
            
            return {"transcription": result, "request_id": request_id}
            
        except Exception as e:
            logger.error("API request failed", exc_info=True)
            raise HTTPException(status_code=500, detail="Transcription failed")
```

### Nested Operations

```python
def transcribe_with_diarization(filename: str) -> str:
    """Example of nested operation contexts."""
    
    with operation_context("full_transcription", filename=filename):
        logger.info("Starting full transcription with diarization")
        
        # Nested operation for audio extraction
        with operation_context("audio_extraction", step="extract"):
            audio_file = extract_audio(filename)
            logger.info("Audio extracted successfully")
        
        # Nested operation for transcription
        with operation_context("whisper_transcription", step="transcribe"):
            transcript = transcribe_audio(audio_file)
            logger.info("Transcription completed")
        
        # Nested operation for diarization
        with operation_context("speaker_diarization", step="diarize"):
            final_result = apply_diarization(transcript, audio_file)
            logger.info("Diarization completed")
        
        logger.info("Full process completed")
        return final_result
```

## Best Practices

### 1. Structured Logging

Always use the `extra` parameter for structured data:

```python
# Good - structured data
logger.info("File processed", extra={
    "filename": "audio.mp3",
    "duration_seconds": 120.5,
    "file_size_mb": 15.2,
    "chunks_created": 3
})

# Avoid - string interpolation loses structure
logger.info(f"Processed {filename} (120.5s, 15.2MB, 3 chunks)")
```

### 2. Use Operation Contexts for Tracking

```python
# Good - trackable operations
with operation_context("video_processing", video_id="123", user_id="user456"):
    logger.info("Processing started")
    process_video()
    logger.info("Processing completed")

# Good - custom correlation ID
with operation_context("batch_job", operation_id="job-2026-001"):
    logger.info("Batch job started")
```

### 3. Exception Logging

```python
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", extra={
        "error_type": type(e).__name__,
        "input_data": sanitized_input
    }, exc_info=True)  # Include stack trace
    raise
```

### 4. Performance Metrics

```python
import time

start_time = time.time()
try:
    result = expensive_operation()
    
    logger.info("Operation completed", extra={
        "duration_seconds": time.time() - start_time,
        "operation": "expensive_operation",
        "result_size": len(result) if result else 0,
        "status": "success"
    })
    
except Exception as e:
    logger.error("Operation failed", extra={
        "duration_seconds": time.time() - start_time,
        "operation": "expensive_operation",
        "status": "error"
    }, exc_info=True)
    raise
```

### 5. Sensitive Data Handling

```python
# Good - sanitize sensitive data
logger.info("User authenticated", extra={
    "user_id": user.id,
    "role": user.role,
    "api_key": "***REDACTED***"  # Never log full API keys
})

# Good - exclude sensitive fields
safe_user_data = {k: v for k, v in user_data.items() 
                  if k not in ['password', 'api_key', 'secret']}
logger.info("User data processed", extra=safe_user_data)
```

## Integration with Monitoring

### Log Aggregation

The JSON format is designed for log aggregation systems:

```python
# Setup for centralized logging
logger = setup_logging(
    dev_mode=False,  # JSON format
    log_file="/var/log/vtt-transcribe/app.json"
)

# Logs can be easily parsed by ELK stack, Fluentd, etc.
logger.info("Event occurred", extra={
    "event_type": "transcription_complete",
    "user_id": "user123",
    "duration_ms": 5000,
    "timestamp": datetime.utcnow().isoformat()
})
```

### Metrics and Alerts

```python
# Structure logs for easy metric extraction
logger.info("API request", extra={
    "method": "POST",
    "endpoint": "/transcribe",
    "status_code": 200,
    "response_time_ms": 1250,
    "user_tier": "premium"
})

# Error patterns for alerting
logger.error("Rate limit exceeded", extra={
    "alert_type": "rate_limit",
    "user_id": user_id,
    "requests_per_minute": 150,
    "limit": 100
})
```

## Migration from Previous Logging

If migrating from basic logging:

```python
# Old style
import logging
logger = logging.getLogger(__name__)
logger.info("Processing file")

# New style - minimal change needed
from vtt_transcribe.logging_config import get_logger
logger = get_logger(__name__)  # Now returns ContextualLoggerAdapter
logger.info("Processing file")  # Same API, enhanced functionality

# Enhanced with context (optional)
with operation_context("file_processing"):
    logger.info("Processing file")  # Now includes operation context automatically
```

## Testing Logging

```python
import io
import json
from vtt_transcribe.logging_config import setup_logging, JsonFormatter

def test_structured_logging():
    """Test that structured logging works correctly."""
    
    # Capture log output
    log_stream = io.StringIO()
    logger = setup_logging(dev_mode=False)  # JSON format
    
    # Replace handler with string capture
    logger.handlers.clear()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    # Log with structured data
    logger.info("Test event", extra={"user_id": "test123", "action": "upload"})
    
    # Parse and verify JSON output
    log_output = log_stream.getvalue()
    log_data = json.loads(log_output.strip())
    
    assert log_data["message"] == "Test event"
    assert log_data["user_id"] == "test123"
    assert log_data["action"] == "upload"
```

## Environment Variables

- `VTT_ENV`: Set to "production" for JSON logging, "development" (or unset) for human-readable
- Standard Python logging env vars also work: `PYTHONPATH`, etc.

## File Locations

For production deployments:

- **Linux**: `/var/log/vtt-transcribe/app.log`
- **Docker**: `/app/logs/vtt-transcribe.log` (with volume mount)
- **Development**: `./logs/vtt-transcribe.log`

## Performance Considerations

- JSON formatting has minimal overhead
- Context variables use Python's contextvars (thread-safe, async-safe)
- Log rotation prevents disk space issues
- Structured fields are more efficient than string interpolation

## Troubleshooting

### Context Not Appearing in Logs

```python
# Make sure to use get_logger, not logging.getLogger
from vtt_transcribe.logging_config import get_logger  # ✓ Correct
logger = get_logger(__name__)

# Not this:
import logging
logger = logging.getLogger(__name__)  # ✗ Won't include context
```

### File Permissions

```bash
# Ensure log directory is writable
sudo mkdir -p /var/log/vtt-transcribe
sudo chown $USER:$USER /var/log/vtt-transcribe
sudo chmod 755 /var/log/vtt-transcribe
```

### Large Log Files

```python
# Ensure rotation is enabled for long-running processes
logger = setup_logging(
    log_file="/path/to/app.log",
    enable_rotation=True,
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5
)
```