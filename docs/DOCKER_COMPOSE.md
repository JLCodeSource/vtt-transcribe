# Docker Compose Setup Guide

This guide explains how to run vtt-transcribe using Docker Compose for local development with a complete stack (API, worker, database, and optional frontend).

## Quick Start

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and set required variables:**
   ```bash
   # REQUIRED: Get from https://platform.openai.com/api-keys
   # Step 1: Generate secure values in your shell (DO NOT paste these lines into .env)
   python -c "import secrets; print(secrets.token_urlsafe(32))"  # for SECRET_KEY
   python -c "import secrets; print(secrets.token_urlsafe(16))"  # for POSTGRES_PASSWORD
   ```
   
   ```bash
   # Step 2: Update your .env file with the generated values:
   # REQUIRED: Get from https://platform.openai.com/api-keys
   OPENAI_API_KEY=sk-your-actual-key-here
   
   # REQUIRED: Paste the 32+ char value generated above
   SECRET_KEY=paste-generated-secret-key-here
   
   # REQUIRED: Paste the database password generated above
   POSTGRES_PASSWORD=paste-generated-db-password-here
   ```
   
   ⚠️ **All three variables above are REQUIRED**. Docker Compose will fail to start if any are missing.

3. **Start services:**
   ```bash
   # Start core services (DB, API, worker)
   docker compose up -d
   
   # Or include frontend (when implemented)
   docker compose --profile frontend up -d
   ```

4. **Verify services are running:**
   ```bash
   docker compose ps
   ```

   You should see:
   - `vtt-transcribe-db` (healthy)
   - `vtt-transcribe-api` (healthy)
   - `vtt-transcribe-worker` (running)

5. **Access the API:**
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Architecture

```
┌─────────────┐
│  Frontend   │ (Optional, port 3000)
│Svelte + Vite│
│ TypeScript  │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐
│  API Server │◄────►│  PostgreSQL  │
│  FastAPI    │      │  Database    │
└──────┬──────┘      └──────────────┘
       │                     ▲
       │                     │
       ▼                     │
┌─────────────┐             │
│   Worker    │─────────────┘
│  Background │
│    Jobs     │
└─────────────┘
```

## Services

### Database (PostgreSQL)
- **Port:** 5432
- **Credentials:** See `.env` file
- **Data:** Persisted in `postgres_data` volume
- **Schema:** Auto-initialized from `docker/init-db.sql`

### API Server (FastAPI)
- **Port:** 8000
- **Image:** Built from Dockerfile (target: `api`)
- **Health:** http://localhost:8000/health
- **Docs:** http://localhost:8000/docs

### Worker
- **Purpose:** Processes transcription jobs in background
- **Concurrency:** Configurable via `WORKER_CONCURRENCY`
- **Shares:** Same database and uploads volume as API

### Frontend (Optional)
- **Port:** 3000
- **Enable:** Add `--profile frontend` to docker compose commands
- **Status:** To be implemented (placeholder service)

## Common Operations

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker
```

### Restart Services
```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart api
```

### Stop Services
```bash
# Stop all (keeps data)
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove everything including data
docker compose down -v
```

### Database Access
```bash
# Connect to PostgreSQL
docker compose exec db psql -U vtt_user -d vtt_transcribe

# Backup database
docker compose exec db pg_dump -U vtt_user vtt_transcribe > backup.sql

# Restore database
docker compose exec -T db psql -U vtt_user vtt_transcribe < backup.sql
```

### Execute Commands in Containers
```bash
# API container shell
docker compose exec api bash

# Run CLI transcription
docker compose exec worker vtt --help
```

## Development Workflow

### Hot Reload (Development Mode)
Edit `.env`:
```bash
API_RELOAD=true
```

Then restart:
```bash
docker compose up -d --build api
```

Changes to Python code will auto-reload the API server.

### Running Tests
```bash
# Run tests on host (recommended)
make test

# Or inside container
docker compose exec api pytest
```

### Debugging
```bash
# Check service health
docker compose ps

# View recent logs
docker compose logs --tail=50 api

# Check environment variables
docker compose exec api env | grep -i api
```

## Environment Variables Reference

See `.env.example` for complete list. Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for Whisper |
| `SECRET_KEY` | Yes | - | JWT signing key (32+ chars) |
| `POSTGRES_PASSWORD` | Yes | - | Database password |
| `HUGGINGFACE_TOKEN` | No | - | For speaker diarization |
| `API_WORKERS` | No | 4 | Uvicorn worker processes |
| `WORKER_CONCURRENCY` | No | 2 | Concurrent transcription jobs |
| `LOG_LEVEL` | No | INFO | Logging verbosity |

## Volumes

- **postgres_data:** Database files (persistent)
- **upload_data:** Uploaded audio/video files (shared by API and worker)
- **./logs:** Application logs (bind mount to host)

## Networking

All services communicate via `vtt-network` bridge network. Service names resolve as hostnames:
- `db` → PostgreSQL
- `api` → FastAPI server
- `worker` → Background worker

## Security Notes

⚠️ **Production Checklist:**

1. **Required environment variables (set in .env):**
   - `OPENAI_API_KEY` - Get from OpenAI platform
   - `SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - `POSTGRES_PASSWORD` - Use a strong random password

   Docker Compose will fail to start if these are not set.

2. **Change default admin user password:**
   - See `docker/init-db.sql` and update the default password hash

3. **Update CORS origins:**
   - Add your production domains to `CORS_ORIGINS`

4. **Enable HTTPS:**
   - Use reverse proxy (nginx, Caddy, Traefik)
   - Don't expose API directly to internet

5. **Review database init:**
   - Remove or change default admin user in `docker/init-db.sql`

## Troubleshooting

### Port already in use
```bash
# Find process using port
sudo lsof -i :8000

# Use different port in .env
API_PORT=8001
```

### Database won't start
```bash
# Check logs
docker compose logs db

# Remove volume and recreate
docker compose down -v
docker compose up -d
```

### API health check fails
```bash
# Check API logs
docker compose logs api

# Verify database connection
docker compose exec api env | grep DATABASE_URL
```

### Worker not processing jobs
```bash
# Check worker logs
docker compose logs worker

# Verify it can connect to database
docker compose exec worker env | grep DATABASE_URL
```

## Next Steps

- Implement frontend (currently placeholder)
- Setup CI/CD for Docker images
- Add monitoring (Prometheus/Grafana)
- Configure production reverse proxy

## Related Documentation

- [Docker Hub Guide](DOCKER_HUB.md)
- [API Documentation](../README.md#api-usage)
- [Contributing Guide](CONTRIBUTING.md)
