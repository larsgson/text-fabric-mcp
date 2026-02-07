# Deployment Guide

## Architecture

Two separate repositories, deployed independently:

```
text-fabric-mcp (this repo)          hebrew-quizz (frontend repo)
├── src/text_fabric_mcp/             ├── src/
│   ├── api.py (FastAPI)             │   ├── App.tsx
│   ├── tf_engine.py                 │   ├── api/client.ts
│   ├── chat.py                      │   └── components/
│   ├── server.py (MCP)              ├── netlify.toml
│   └── quiz_engine.py               ├── package.json
├── Dockerfile                       └── .env.example
└── system_prompt.md

Deployed to:                         Deployed to:
  Fly.io / Railway / VPS               Netlify (static hosting)
  Serves /api/* endpoints               Calls VITE_API_URL/api/*
```

---

## Backend: text-fabric-mcp

### Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Start the API server
tf-api

# Run tests
pytest
```

The API runs at `http://localhost:8000`. First request loads Text-Fabric corpora into memory (~10s).

### Deploy to Fly.io

#### Install CLI and log in

```bash
brew install flyctl        # macOS
fly auth login
```

#### Launch

```bash
fly launch
```

Edit the generated `fly.toml`:

```toml
app = "text-fabric-mcp"
primary_region = "ams"

[build]

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "suspend"
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = "1gb"
  cpu_kind = "shared"
  cpus = 1
```

#### Create persistent volumes

```bash
fly volumes create tf_data --size 1 --region ams
fly volumes create quiz_data --size 1 --region ams
```

Add to `fly.toml`:

```toml
[[mounts]]
  source = "tf_data"
  destination = "/root/text-fabric-data"

[[mounts]]
  source = "quiz_data"
  destination = "/app/quizzes"
```

#### Set secrets

```bash
fly secrets set ANTHROPIC_API_KEY=sk-ant-your-key-here   # optional, for chat
```

#### Deploy

```bash
fly deploy
```

#### Pre-warm corpus cache

```bash
fly ssh console -C "python -c \"from tf.app import use; use('ETCBC/bhsa', silent='deep'); use('ETCBC/nestle1904', silent='deep')\""
```

#### Health check

Add to `fly.toml`:

```toml
[[services.http_checks]]
  interval = 30000
  timeout = 5000
  path = "/api/corpora"
```

### Deploy to Railway

#### Setup

1. Go to [railway.app](https://railway.app) and sign up
2. Create new project > Deploy from GitHub Repo > select `text-fabric-mcp`
3. Railway auto-detects the Dockerfile

#### Configure

In the Railway dashboard:

**Networking:** Click "Generate Domain" for a public URL.

**Volumes:** Add two:

| Name | Mount Path | Size |
|------|-----------|------|
| tf-data | /root/text-fabric-data | 1 GB |
| quiz-data | /app/quizzes | 1 GB |

**Variables:**

```
PORT=8000
ANTHROPIC_API_KEY=sk-ant-your-key-here   # optional, for chat
```

#### Deploy

Push to GitHub — Railway auto-deploys. Or use CLI:

```bash
npm install -g @railway/cli
railway login
railway up
```

---

## Frontend: hebrew-quizz

### Local Development

```bash
cd frontend/    # or the hebrew-quizz repo
pnpm install
pnpm dev
```

Vite proxies `/api` to `http://localhost:8000` during development.

### Environment Variable

Set `VITE_API_URL` to point to the deployed backend:

```bash
# .env (or Netlify dashboard)
VITE_API_URL=https://text-fabric-mcp.fly.dev
```

Leave empty for local development (uses Vite proxy).

### Deploy to Netlify

#### Option A: Connect GitHub repo

1. Go to [netlify.com](https://netlify.com) and sign up
2. Click "Add new site" > "Import an existing project"
3. Connect your GitHub account > select the `hebrew-quizz` repo
4. Build settings are auto-detected from `netlify.toml`:
   - Build command: `pnpm build`
   - Publish directory: `dist`
5. Set environment variable in Netlify dashboard:
   - `VITE_API_URL` = `https://text-fabric-mcp.fly.dev` (your deployed API URL)
6. Deploy

#### Option B: CLI deploy

```bash
npm install -g netlify-cli
netlify login
netlify init
netlify deploy --prod
```

#### SPA Routing

The `netlify.toml` includes a redirect rule that serves `index.html` for all routes, enabling React Router to work correctly.

---

## Summary

| | Backend (text-fabric-mcp) | Frontend (hebrew-quizz) |
|---|---|---|
| **Stack** | Python, FastAPI, Text-Fabric | React, TypeScript, Vite |
| **Deploy to** | Fly.io or Railway | Netlify |
| **Persistent storage** | ~/text-fabric-data (~400MB), quizzes/ | None (static site) |
| **Env vars** | ANTHROPIC_API_KEY (optional) | VITE_API_URL (required in prod) |
| **Cost** | ~$5-7/month (Fly.io 1GB) | Free (Netlify free tier) |
| **Health check** | GET /api/corpora | N/A |
