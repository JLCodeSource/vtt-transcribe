# Devcontainer Configuration

This devcontainer uses docker-compose to connect to the `vtt-transcribe_vtt-network` so it can access all docker-compose services (db, api, worker, frontend).

## ⚠️ Prerequisites

**IMPORTANT**: Before opening the devcontainer, you **must** create the external network:

```bash
# Option 1: Start the main docker-compose stack (creates network + services)
docker-compose up -d

# Option 2: Just create the network (if you don't need the services running)
docker network create vtt-transcribe_vtt-network
```

Without this, the devcontainer will fail with:  
`network vtt-transcribe_vtt-network declared as external, but could not be found`

## GPU Support (Optional)

The devcontainer is configured with **optional GPU support**:
- On GPU hosts with nvidia-docker: GPU acceleration is automatically available
- On non-GPU hosts: Container runs normally without GPU (no errors)
- Controlled by `hostRequirements.gpu: "optional"` in devcontainer.json

VS Code's devcontainer extension handles GPU detection and gracefully falls back when GPUs are unavailable. No configuration changes needed - it just works on both GPU and non-GPU hosts!

## Network Access

The devcontainer connects to the external `vtt-transcribe_vtt-network` network. This requires:
1. The main docker-compose stack to be running (to create the network)
2. Run: `docker-compose up -d` from the project root before opening the devcontainer

Once connected, you can access services by name:
- `db` - PostgreSQL database on port 5432
- `api` - FastAPI backend on port 8000  
- `worker` - Background worker (no direct port)
- `frontend` - Svelte frontend on port 3000

Environment variables are pre-configured:
- `DATABASE_URL=postgresql://vtt_user:$POSTGRES_PASSWORD@db:5432/vtt_transcribe`
- `API_URL=http://api:8000`
