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
│   │       ├── documents.py    # Document management & search endpoints
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
│   ├── test_documents.py       # Ingest & search endpoint tests
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

## Internal Admin UI

The API ships with a built-in admin interface — no curl commands required.

```
GET http://localhost:8000/ui
```

Features:
- **Upload Document** — select a PDF, fill metadata, click submit. The file is uploaded
  to MinIO, database rows are created, and (by default) the full ingestion pipeline runs
  immediately: download → parse → chunk → embed.
- **Semantic Search** — type a natural-language query, get back matching chunks with
  similarity scores.

> The UI calls the same REST API endpoints described below.

---

## Manual Ingestion Flow (MVP)

> **Tip:** The Admin UI (`GET /ui`) automates steps 1–3 in a single form submission.

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
         "tags": ["Parsing", "Embeddings"],
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

5. **Semantic Document Search**:
   Call the search endpoint to search for document chunks semantically across the knowledge base:
   ```bash
   curl -X POST http://localhost:8000/api/v1/documents/search \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What is the role of OpenClaw in the leadgen architecture?",
       "limit": 5,
       "filters": {
         "type": "case",
         "client_name": "Acme Corp",
         "industry": null,
         "geography": null,
         "use_case": null,
         "tags": []
       }
     }'
   ```
   This will return matched chunks ordered by vector similarity score (cosine distance).

   Example response:
   ```json
   {
     "query": "What is the role of OpenClaw in the leadgen architecture?",
     "results": [
       {
         "document_id": "d7c1775d-3549-4eb0-bb82-411a5b8a07c2",
         "title": "Expanded Leadgen Product Requirements Document",
         "type": "case",
         "client_name": "Acme Corp",
         "industry": "Technology",
         "geography": "Global",
         "use_case": "Lead Gen Integration",
         "tags": ["AI", "Machine Learning"],
         "authors": ["Sergii Poznokos"],
         "source_bucket": "leadgen-docs",
         "source_object_key": "leadgen_prd_expanded.pdf",
         "chunk_id": "8a329d4c-cbe4-432d-862d-986c5512140a",
         "chunk_index": 0,
         "content": "OpenClaw orchestrates the ingest workflow by coordinating the parser and embedding logic...",
         "score": 0.87
       }
     ]
   }
   ```

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

### Document Ingestion, Management & Search
- **POST** `/api/v1/documents/upload` - Upload a PDF (`multipart/form-data`) and optionally
  process it immediately (parse → chunk → embed). Returns `chunks_created` when done.
- **POST** `/api/v1/documents/ingest` - Register metadata for a file already in MinIO and
  schedule a pending ingestion job.
- **GET** `/api/v1/documents` - List all documents in the directory, including computed chunk counts.
- **GET** `/api/v1/documents/{document_id}` - Get details and metadata for a specific document.
- **PATCH** `/api/v1/documents/{document_id}` - Update a document's title and metadata (does not trigger re-ingest).
- **POST** `/api/v1/documents/{document_id}/reingest` - Rebuild Search Index from the existing source file (requires a valid `reason`).
- **POST** `/api/v1/documents/{document_id}/replace-file` - Upload a new version of the file, update database source references, and rebuild the search index immediately.
- **POST** `/api/v1/documents/{document_id}/archive` - Archive a document (sets status to `'archived'`).
- **POST** `/api/v1/documents/{document_id}/restore` - Restore an archived document.
- **GET** `/api/v1/documents/{document_id}/jobs` - Get ingestion job runs associated with a document.
- **POST** `/api/v1/documents/search` - Semantic search using pgvector cosine similarity.

### Ingestion Queue & Job Operations
- **POST** `/api/v1/ingestion/process-next` - Claim and run the next pending ingestion job in the database.
- **GET** `/api/v1/ingestion/jobs` - List all ingestion jobs with optional query filtering by `status` and `document_id` plus pagination (`limit`, `offset`).
- **GET** `/api/v1/ingestion/jobs/{job_id}` - Get specific job details including status and failure error message.
- **POST** `/api/v1/ingestion/jobs/{job_id}/retry` - Reset a failed job to `'pending'` and related document to `'uploaded'`, with option to `process_immediately`.

### Admin UI
- **GET** `/ui` - Internal admin interface for uploading/managing documents, viewing job runs, and executing semantic searches.


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

## Docker deployment

GitHub Actions builds and pushes images to GitHub Container Registry (GHCR) on pushes to the `main` branch.

- **Production image**: `ghcr.io/sergeo-13/leadgen-api:prod`
- **Development image**: `ghcr.io/sergeo-13/leadgen-api:dev`

### Hostinger Docker Manager Configuration
When deploying on Hostinger Docker Manager, configure it to pull using `image:` instead of building locally with `build:`.

- **Production deployment** (`docker-compose.prod.yml`):
  - Service: `leadgen-api`
  - Container name: `leadgen-api`
  - Port mapping: `8000:8000` (external `8000` mapped to container `8000`)
- **Development deployment** (`docker-compose.dev.yml`):
  - Service: `leadgen-api-dev`
  - Container name: `leadgen-api-dev`
  - Port mapping: `3001:8000` (external `3001` mapped to container `8000`)

> [!IMPORTANT]
> After the first successful GitHub Actions build, you may need to go to your GitHub Package settings and make the package public so Hostinger can pull the image without requiring registry authentication.

## License

MIT

