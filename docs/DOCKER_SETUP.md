# Docker Compose Setup Guide

## Quick Start

### 1. Create Environment File
```bash
cp .env.example .env
# Edit .env with your actual credentials
nano .env  # or use VS Code
```

**Required variables:**
- `POSTGRES_PASSWORD` - Set a secure password
- `OPENAI_API_KEY` - Your OpenAI API key
- `SECRET_KEY` - Random string for JWT signing

**Optional variables:**
- `HUGGINGFACE_TOKEN` - For speaker diarization features

### 2. Start Services
```bash
# Start all services (except frontend)
docker-compose up -d

# Or start with frontend
docker-compose --profile frontend up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 3. Access from Devcontainer

The devcontainer automatically joins the `vtt-network`, so you can access services by their service names:

**PostgreSQL:**
```bash
# Connection string (using service name 'db')
postgresql://vtt_user:your_password@db:5432/vtt_transcribe

# Or use psql
psql -h db -p 5432 -U vtt_user -d vtt_transcribe
```

**FastAPI:**
```bash
# HTTP requests from devcontainer (using service name 'api')
curl http://api:8000/api/health

# Environment variable available
echo $API_URL  # http://api:8000
```

**Frontend:**
```bash
# Access by service name
curl http://frontend
```

### 4. Access from Windows Host

Once services are running, access directly on localhost:

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **PostgreSQL**: `localhost:5432`
- **Frontend**: http://localhost:3000 (if enabled)

### 5. Testing the Setup

**From Devcontainer:**
```bash
# Test database connection (using service name 'db')
uv run python -c "
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect(
        'postgresql://vtt_user:your_password@db:5432/vtt_transcribe'
    )
    version = await conn.fetchval('SELECT version()')
    print(f'Connected! PostgreSQL {version}')
    await conn.close()

asyncio.run(test())
"

# Test API connection (using service name 'api')
curl -s http://api:8000/api/health | jq
```

**From Windows Host (PowerShell):**
```powershell
# Test API
curl http://localhost:8000/api/health

# Test PostgreSQL (if you have psql installed)
psql -h localhost -p 5432 -U vtt_user -d vtt_transcribe
```

## Network Architecture

The devcontainer joins the `vtt-network` docker network, allowing direct communication with services:

| Port | Service    | Access from Devcontainer | Access from Windows Host |
|------|------------|--------------------------|--------------------------|
| 5432 | PostgreSQL | `db:5432`                | `localhost:5432`         |
| 8000 | FastAPI    | `api:8000`               | `localhost:8000`         |
| 3000 | Frontend   | `frontend:80`            | `localhost:3000`         |

**Why this works:**
- Docker-compose creates `vtt-transcribe_vtt-network` bridge network
- All services (db, api, worker, frontend) connect to this network
- Devcontainer joins the same network via `runArgs`
- Services communicate via Docker's internal DNS (service names)
- Docker-compose port mappings expose services to Windows host

## Troubleshooting

### Services not accessible from devcontainer

**Use service names** (Docker DNS), not `localhost`:
```bash
# ❌ Wrong
curl http://localhost:8000/health

# ✅ Correct (devcontainer is on same network)
curl http://api:8000/api/health
psql -h db -U vtt_user
```

**If network connection fails:**
1. Check devcontainer is on the network:
   ```bash
   docker network inspect vtt-transcribe_vtt-network
   # Should show your devcontainer in Containers list
   ```

2. Restart devcontainer if you started docker-compose after devcontainer:
   ```bash
   # From VS Code: Ctrl+Shift+P → "Rebuild Container"
   ```

### Ports not accessible from Windows host

1. **Check services are running:**
   ```bash
   docker-compose ps
   ```

2. **Check port bindings:**
   ```bash
   docker ps --format "table {{.Names}}\t{{.Ports}}"
   ```

3. **Verify .env file has correct ports:**
   ```bash
   grep PORT .env
   ```

4. **Check Windows Firewall:**
   - Allow Docker Desktop through firewall
   - Allow WSL2 network access

### Database connection refused

1. **Wait for database to be healthy:**
   ```bash
   docker-compose ps db
   # Should show "healthy" status
   ```

2. **Check database logs:**
   ```bash
   docker-compose logs db
   ```

3. **Verify password in .env:**
   ```bash
   grep POSTGRES_PASSWORD .env
   ```

### Port already in use

```bash
# Find what's using the port (Windows PowerShell)
netstat -ano | findstr :8000

# Stop the process or change port in .env
API_PORT=8001  # Use different port
```

## Environment Variables Reference

See `.env.example` for all available configuration options.

**Critical settings:**
- Database credentials must match in all services
- `DATABASE_URL` uses service name `db` (Docker DNS resolution)
- Devcontainer joins `vtt-network`, uses service names (db, api, etc.)
- Windows host uses `localhost` (docker-compose port mappings)

## Advanced: Network Configuration

The docker-compose setup uses a custom bridge network `vtt-network`:

```bash
# Inspect network
docker network inspect vtt-transcribe_vtt-network

# See connected containers
docker network inspect vtt-transcribe_vtt-network --format '{{range .Containers}}{{.Name}} {{end}}'
```

**How service discovery works:**
- Devcontainer joins `vtt-network` via `runArgs`
- Docker's embedded DNS resolves service names (db → 172.x.x.x)
- All containers on same network communicate directly
- Windows host accesses via `localhost` through port mappings

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v

# Stop specific service
docker-compose stop api
```

## Rebuilding After Changes

```bash
# Rebuild specific service
docker-compose build api

# Rebuild and restart
docker-compose up -d --build api

# Rebuild everything
docker-compose build --no-cache
docker-compose up -d
```
