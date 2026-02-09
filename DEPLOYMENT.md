# Deployment Guide

## Google Gemini API Key (for chat)

The `/api/chat` endpoint uses Google Gemini. A free-tier key is sufficient.

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with a Google account
3. Click **Create API Key**
4. Copy the key and set it as `GOOGLE_API_KEY` in your deployment environment

Free tier limits: 15 requests/minute, 1,000 requests/day, 250,000 tokens/minute (Gemini 2.5 Flash-Lite). No credit card required.

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

#### Create persistent volume

```bash
fly volumes create app_data --size 1 --region ams
```

Add to `fly.toml`:

```toml
[[mounts]]
  source = "app_data"
  destination = "/data"
```

#### Set secrets

```bash
fly secrets set API_KEY=your-shared-secret-here           # recommended, locks down the API
fly secrets set GOOGLE_API_KEY=your-gemini-key-here       # optional, for chat (free tier)
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
  path = "/health"
```

### Deploy to Railway

#### Setup

1. Go to [railway.app](https://railway.app) and sign up
2. Create new project > Deploy from GitHub Repo > select `text-fabric-mcp`
3. Railway auto-detects the Dockerfile

#### Configure

In the Railway dashboard:

**Networking:** Click "Generate Domain" for a public URL.

**Volume:** Add one:

| Name | Mount Path | Size |
|------|-----------|------|
| app-data | /data | 1 GB |

**Variables:**

```
PORT=8000
API_KEY=your-shared-secret-here           # recommended, locks down the API
GOOGLE_API_KEY=your-gemini-key-here       # optional, for chat (free tier)
```

#### Deploy

Push to GitHub — Railway auto-deploys. Or use CLI:

```bash
npm install -g @railway/cli
railway login
railway up
```

---

## Frontend Integration

The API is protected by an `API_KEY`. A frontend deployed on Netlify should use an edge function to proxy `/api/*` requests and inject the key server-side. See the frontend repository for deployment instructions.
