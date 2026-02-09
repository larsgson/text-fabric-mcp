# Deployment Guide

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
fly secrets set API_KEY=your-shared-secret-here           # recommended, locks down the API
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

**Volumes:** Add two:

| Name | Mount Path | Size |
|------|-----------|------|
| tf-data | /root/text-fabric-data | 1 GB |
| quiz-data | /app/quizzes | 1 GB |

**Variables:**

```
PORT=8000
API_KEY=your-shared-secret-here           # recommended, locks down the API
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

## Frontend Integration

The API is protected by an `API_KEY`. A frontend deployed on Netlify should use an edge function to proxy `/api/*` requests and inject the key server-side. See the frontend repository for deployment instructions.
