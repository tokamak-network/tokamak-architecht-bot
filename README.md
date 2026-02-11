# Tokamak Architect Bot

AI-powered chatbot for the Tokamak Rollup Hub (TRH) platform. Helps users deploy and manage L2 rollup chains.

## Features

- **Q&A from Documentation**: Answers questions about rollup deployment, configuration parameters, and best practices
- **RAG-powered**: Uses Retrieval Augmented Generation for accurate, documentation-based responses
- **Claude Integration**: Powered by Claude (Anthropic) via Tokamak AI Gateway
- **Swappable Embeddings**: Supports local (free), OpenAI, or Tokamak embeddings
- **Conversation History**: Maintains context across multiple messages

## Quick Start

### Prerequisites

- Python 3.11+
- Tokamak AI Gateway API key

### Installation

```bash
# Clone the repository
cd tokamak-architecht-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your API key
```

### Configuration

Edit `.env` file:

```env
# Required: Tokamak AI Gateway
TOKAMAK_AI_BASE_URL=https://api.ai.tokamak.network
TOKAMAK_AI_API_KEY=your-api-key-here

# Chat model (served via Tokamak AI Gateway)
# Default: Qwen3 80B Next
# Example:
# CHAT_MODEL=qwen3-80b-next
# Other options depend on gateway configuration (e.g. qwen3-235b, claude-sonnet-4.5)
CHAT_MODEL=qwen3-80b-next

# Embedding provider: "local" (free), "openai", or "tokamak"
EMBEDDING_PROVIDER=local
```

### Run Document Ingestion

Before first use, ingest documentation into the vector store:

```bash
python -m scripts.ingest
```

### Start the Server

```bash
# Development mode (with auto-reload)
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## API Endpoints

### Chat

```bash
POST /api/chat
```

**Request:**
```json
{
  "message": "What is the challenge period?",
  "conversation_id": "optional-uuid",
  "history": []
}
```

**Response:**
```json
{
  "response": "The challenge period is...",
  "conversation_id": "uuid",
  "sources": ["tokamak-docs/deployment.md"],
  "model": "qwen3-80b-next",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Health Check

```bash
GET /health
```

## Docker

### Build

```bash
docker build -t tokamak-architect-bot .
```

### Run

```bash
docker run -d \
  -p 8001:8001 \
  -e TOKAMAK_AI_API_KEY=your-key \
  -v $(pwd)/data:/app/data \
  tokamak-architect-bot
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TOKAMAK ARCHITECT BOT                     │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  FastAPI    │  │  RAG        │  │  Tokamak Gateway   │  │
│  │  Server     │→ │  Service    │→ │  (Claude API)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │               │                                    │
│         │               ▼                                    │
│         │        ┌─────────────┐                            │
│         │        │  Chroma     │                            │
│         │        │  Vector DB  │                            │
│         │        └─────────────┘                            │
│         │               ▲                                    │
│         │               │                                    │
│         │        ┌─────────────┐                            │
│         └───────→│  Embedding  │                            │
│                  │  Service    │                            │
│                  │ (swappable) │                            │
│                  └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

## Embedding Providers

The bot supports multiple embedding providers. Change `EMBEDDING_PROVIDER` in `.env`:

| Provider | Config Value | Cost | Requirements |
|----------|--------------|------|--------------|
| Local (sentence-transformers) | `local` | Free | None |
| OpenAI | `openai` | ~$0.02/1M tokens | `OPENAI_API_KEY` |
| Tokamak Gateway | `tokamak` | Depends | When available |

## Project Structure

```
tokamak-architecht-bot/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── chat.py      # Chat endpoints
│   │       └── health.py    # Health check
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── services/
│   │   ├── embedding_service.py  # Swappable embeddings
│   │   ├── llm_service.py        # Claude integration
│   │   └── rag_service.py        # RAG pipeline
│   ├── utils/
│   │   └── prompts.py       # System prompts
│   ├── config.py            # Configuration
│   └── main.py              # FastAPI app
├── scripts/
│   └── ingest.py            # Document ingestion
├── data/
│   └── chroma_db/           # Vector store
├── Dockerfile
├── requirements.txt
└── README.md
```

## Security

- **Never stores** private keys, seed phrases, or AWS credentials
- **Never executes** transactions or signs messages
- All sensitive operations require manual user confirmation
- API key required for access

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black app/ scripts/
isort app/ scripts/
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please open a GitHub issue.
