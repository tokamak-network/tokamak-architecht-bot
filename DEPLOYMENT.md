# Tokamak Architect Bot - Deployment Guide

## Quick Reference

| Environment | Chatbot URL | Frontend URL |
|-------------|-------------|--------------|
| Local Dev | http://localhost:8001 | http://localhost:3000 |
| Docker Local | http://localhost:8001 | http://localhost:3000 |
| Production | https://your-domain:8001 | https://your-domain |

---

## Option 1: Standalone Docker Deployment

Best for testing the chatbot independently.

### Steps

```bash
# 1. Clone and enter directory
cd tokamak-architecht-bot

# 2. Create .env from example
cp .env.example .env

# 3. Edit .env with your API key
nano .env
# Set: TOKAMAK_AI_API_KEY=your-actual-key

# 4. Build and start
docker-compose up -d

# 5. Ingest documentation (first time only)
docker-compose exec chatbot python -m scripts.ingest

# 6. Verify it's running
curl http://localhost:8001/health

# 7. View logs
docker-compose logs -f chatbot
```

### Stop / Restart

```bash
docker-compose down        # Stop
docker-compose up -d       # Start
docker-compose restart     # Restart
```

---

## Option 2: Integrate with TRH Platform

Best for production deployment alongside the main platform.

### Prerequisites

1. `trh-platform` repo cloned and working
2. `tokamak-architecht-bot` repo cloned in the same parent directory

```
parent-folder/
├── trh-platform/
├── trh-platform-ui/
└── tokamak-architecht-bot/
```

### Steps

1. **Add chatbot service to docker-compose.yml**

   Copy the service definition from `docker-compose.trh-integration.yml` into your `trh-platform/docker-compose.yml`.

2. **Add environment variables**

   In `trh-platform/.env`:
   ```env
   TOKAMAK_AI_API_KEY=your-api-key-here
   CHATBOT_CORS_ORIGINS=https://your-production-domain.com
   ```

3. **Update Terraform security group**

   Add inbound rule for port 8001:
   ```hcl
   ingress {
     from_port   = 8001
     to_port     = 8001
     protocol    = "tcp"
     cidr_blocks = ["0.0.0.0/0"]
     description = "Tokamak Architect Bot API"
   }
   ```

4. **Update frontend environment**

   In `trh-platform-ui/.env.production`:
   ```env
   NEXT_PUBLIC_CHATBOT_URL=https://your-domain.com:8001
   ```

5. **Deploy**

   ```bash
   docker-compose up -d --build
   docker-compose exec chatbot python -m scripts.ingest
   ```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TOKAMAK_AI_API_KEY` | Yes | - | API key for Tokamak AI Gateway |
| `TOKAMAK_AI_BASE_URL` | No | https://api.ai.tokamak.network | AI Gateway URL |
| `CHAT_MODEL` | No | qwen3-80b-next | Chat model to use (default Qwen3 80B Next) |
| `EMBEDDING_PROVIDER` | No | local | local, openai, or tokamak |
| `CORS_ORIGINS` | No | http://localhost:3000 | Allowed frontend origins |
| `LOG_LEVEL` | No | INFO | Logging level |
| `PORT` | No | 8001 | Server port |

---

## Troubleshooting

### Chatbot not responding

```bash
# Check if container is running
docker ps | grep chatbot

# Check logs
docker-compose logs chatbot

# Test health endpoint
curl http://localhost:8001/health
```

### CORS errors in browser

1. Check `CORS_ORIGINS` includes your frontend URL
2. Restart the chatbot after changing CORS settings
3. Clear browser cache

### Empty responses / No context

Documents may not be ingested:
```bash
docker-compose exec chatbot python -m scripts.ingest
```

### Docker build fails

```bash
# Check Docker is running
docker info

# Rebuild without cache
docker-compose build --no-cache
```

---

## Updating Documentation

To add more documents to the chatbot's knowledge base:

1. Add documents to `scripts/ingest.py` (URL or inline content)
2. Run ingestion:
   ```bash
   docker-compose exec chatbot python -m scripts.ingest
   ```

---

## Monitoring

### Health Check

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "tokamak-architect-bot",
  "version": "1.0.0"
}
```

### Logs

```bash
# Follow logs
docker-compose logs -f chatbot

# Last 100 lines
docker-compose logs --tail=100 chatbot
```

---

## Security Notes

- Never commit `.env` files with real API keys
- Use environment variables or secrets management in production
- The chatbot never stores or handles private keys/seed phrases
- All sensitive operations require manual user confirmation
