# PROJECT_CONTEXT (Historical Context / Reference Only)

> [!NOTE]
> This document details the initial MVP scope and project context from the beginning of the project. It is preserved here for historical reference only. For the current architecture, features, and endpoints, please refer to the main [README.md](../README.md) and [docs/ARCHITECTURE.md](ARCHITECTURE.md).

---

# Leadgen API — Project Context

## Goal

Build a small backend API for the Leadgen Agent Platform based on OpenClaw.

OpenClaw is the orchestration/chat/gateway layer. It should not store documents or embeddings directly. It calls this API as a tool/service.

## Current Infrastructure

VPS: Hostinger KVM 2
Docker network: leadgen_net

Services already deployed:

- OpenClaw Leadgen instance: leadgen-bot
- MinIO: minio:9000
- MinIO bucket: leadgen-docs
- Postgres with pgvector: leadgen-postgres:5432
- Database: leadgen
- User: leadgen

## Storage Responsibilities

- MinIO stores original files: PDF, PPTX, DOCX.
- Postgres stores metadata, ingestion jobs, document chunks.
- pgvector stores embeddings for semantic search.
- OpenClaw calls leadgen-api; it does not directly parse/index documents.

## Existing Postgres Tables

- documents
- document_chunks
- ingestion_jobs

document_chunks.embedding is vector(1536).

## MVP Scope

Supported file types:

- PDF
- PPTX
- DOCX

Initial document volume: up to 20 files.

MVP endpoints:

- GET /health
- POST /documents/ingest
- POST /documents/search
- GET /documents/{document_id}
- GET /documents
- PATCH /documents/{document_id}/metadata

## First Implementation Step

Implement only:

GET /health

It should check:
- Postgres connectivity
- MinIO connectivity
- MinIO bucket leadgen-docs exists

Return:

{
  "status": "ok",
  "postgres": "ok",
  "minio": "ok"
}

No ingestion logic yet.

## Tech Stack

- Python 3.12
- FastAPI
- Uvicorn
- psycopg
- boto3
- OpenAI SDK later
- python-pptx later
- python-docx later
- pypdf later

## Deployment

This repo must include:

- Dockerfile
- docker-compose.yml
- requirements.txt
- main.py
- .env.example
- README.md

Docker Compose must attach the API to external network:

leadgen_net

Do not include MinIO or Postgres containers in this compose file.
