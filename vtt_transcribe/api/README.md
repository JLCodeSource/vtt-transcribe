# vtt-transcribe FastAPI Web Service

REST API for transcribing audio and video files using OpenAI's Whisper model.

## Quick Start

### Installation

Install with API support:

```bash
pip install vtt-transcribe[api]
```

### Running the Server

Start the development server:

```bash
vtt-api
```

The API will be available at `http://localhost:8000`

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API Endpoints

### Health Check

```bash
GET /health
```

Returns the health status and version of the API.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.3.1"
}
```

### Create Transcription Job

```bash
POST /transcribe
```

Upload an audio or video file for transcription.

**Request:**
- `file`: Audio/video file (multipart/form-data)
- `api_key`: OpenAI API key (form field)

**Supported formats**: MP3, MP4, WAV, M4A, OGG

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Transcription job created"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -F "file=@audio.mp3" \
  -F "api_key=sk-..."
```

### Get Job Status

```bash
GET /jobs/{job_id}
```

Check the status of a transcription job.

**Response (Pending):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "filename": "audio.mp3"
}
```

**Response (Completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "filename": "audio.mp3",
  "result": "[00:00 - 00:05] Hello, this is a test transcript..."
}
```

**Response (Failed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "filename": "audio.mp3",
  "error": "API authentication failed"
}
```

## Development

### Running Tests

```bash
# Run API tests only
pytest tests/test_api/ -v

# Run all tests
make test
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint
```

## Architecture

- **Framework**: FastAPI with async/await support
- **Job Processing**: Asynchronous background tasks
- **File Handling**: Temporary files cleaned up automatically
- **CORS**: Enabled for all origins (configure for production)

## Roadmap

This is the foundational implementation for v0.4.0. Future enhancements:

- [ ] WebSocket support for real-time progress updates
- [ ] User authentication and API key management
- [ ] Database integration for job persistence
- [ ] Speaker diarization endpoints
- [ ] Translation endpoints
- [ ] Web frontend

## Configuration

### Production Deployment

For production use, configure:

1. **CORS origins**: Update `app.py` to restrict origins
2. **HTTPS**: Use a reverse proxy (nginx, Caddy)
3. **Workers**: Run with multiple workers (`uvicorn --workers 4`)
4. **File limits**: Configure max upload size
5. **Rate limiting**: Add rate limiting middleware

### Environment Variables

- `OPENAI_API_KEY`: Default API key (optional, can be provided per-request)
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

## License

BSD-3-Clause
