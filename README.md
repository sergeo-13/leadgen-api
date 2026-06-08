# Leadgen Bot - AI-Powered Lead Generation Platform

A FastAPI-based service for intelligent lead generation and processing.

## Project Structure

```
leadgen-bot/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # Authentication & authorization
│   │   └── exceptions.py       # Custom exceptions
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py       # Health check endpoints
│   │       ├── documents.py    # Document management endpoints
│   │       └── ingestion.py    # Ingestion processing endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database.py         # Database connection management
│   │   ├── minio_service.py    # MinIO operations
│   │   ├── document_parser.py  # PDF text extraction
│   │   ├── chunker.py          # Text chunking logic
│   │   ├── embedding_service.py # OpenAI embeddings generation
│   │   └── ingestion_service.py # Ingestion coordination logic
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic schemas
│   └── utils/
│       ├── __init__.py
│       └── logging.py          # Logging configuration
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest configuration
│   ├── test_health.py          # Health endpoint tests
│   ├── test_documents.py       # Ingest endpoint tests
│   └── test_ingestion.py       # Ingestion process endpoint tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local development)

### Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Update with your configuration
vim .env
```

### Running with Docker Compose

```bash
# Start the service
docker-compose up -d --build

# Check health
curl http://localhost:8000/health
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Run with uvicorn
uvicorn src.main:app --reload --port 8000
```

## Manual Ingestion Flow (MVP)

To manually ingest and process a document in the current MVP version:

1. **Upload File to MinIO**:
   Upload your target PDF document (e.g. `leadgen_prd_expanded.pdf`) manually to the MinIO bucket `leadgen-docs`.

2. **Ingest Document Metadata**:
   Call the ingest endpoint to create the database rows and queue the ingestion job:
   ```bash
   curl -X POST http://localhost:8000/api/v1/documents/ingest \
     -H "Content-Type: application/json" \
     -d '{
       "object_key": "leadgen_prd_expanded.pdf",
       "title": "Expanded Leadgen Product Requirements Document",
       "metadata": {
         "type": "case",
         "client_name": "Acme Corp",
         "industry": "Technology",
         "geography": "Global",
         "use_case": "Lead Gen Integration",
         "capabilities": ["Parsing", "Embeddings"],
         "authors": ["System Architect"]
       }
     }'
   ```
   This will return a `document_id` and an ingestion `job_id` with a status of `"pending"`.

3. **Process Ingestion Job**:
   Trigger the next pending job in the queue to download, parse, chunk, and embed the document:
   ```bash
   curl -X POST http://localhost:8000/api/v1/ingestion/process-next
   ```
   If successful, it returns:
   ```json
   {
     "status": "completed",
     "job_id": "<job_id>",
     "document_id": "<document_id>",
     "chunks_created": N
   }
   ```

4. **Verify Chunks**:
   Check the `document_chunks` table in PostgreSQL to verify that the chunks and embeddings were successfully created for your `document_id`.

## API Endpoints

### Health Check
- **GET** `/health` - System health status (or `/api/v1/health`)

```json
{
  "status": "ok",
  "postgres": "ok",
  "minio": "ok",
  "version": "0.1.1"
}
```

### Document Ingestion
- **POST** `/api/v1/documents/ingest` - Registers metadata and schedules a pending job.
- **POST** `/api/v1/ingestion/process-next` - Claims and runs the next pending job.

## Configuration

All configuration is managed through environment variables. See `.env.example` for all available options.

### PostgreSQL
- `POSTGRES_HOST` - Database host
- `POSTGRES_PORT` - Database port
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password

### MinIO
- `MINIO_ENDPOINT` - MinIO endpoint URL
- `MINIO_ACCESS_KEY` - MinIO access key
- `MINIO_SECRET_KEY` - MinIO secret key
- `MINIO_BUCKET` - Default bucket name
- `MINIO_SECURE` - Use HTTPS for MinIO

### OpenAI
- `OPENAI_API_KEY` - OpenAI Secret API Key (needed for embedding generation)
- `EMBEDDING_MODEL` - Embedding model to use (defaults to `text-embedding-3-small`)

## Development

### Running Tests

```bash
pip install pytest pytest-asyncio pytest-cov
pytest tests/ -v --cov=src
```

### Code Quality

```bash
pip install black flake8 mypy
black src/
flake8 src/
mypy src/
```

## Deployment

The service is containerized and ready for deployment in any Docker-compatible environment (Kubernetes, Docker Swarm, etc.).

## License

MIT
