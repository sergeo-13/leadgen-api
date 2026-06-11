# Architecture

## High-Level Architecture

```text
User
  ↓
OpenClaw Leadgen Agent
  ↓
Leadgen API
  ↓
┌─────────────────────┬─────────────────────┐
│       MinIO         │  PostgreSQL+pgvector│
└─────────────────────┴─────────────────────┘
```

## Component Responsibilities

### OpenClaw

Role:

* Gateway
* Orchestrator
* Agent Runtime

Responsibilities:

* Chat interface
* Agent execution
* Tool invocation
* Workflow orchestration
* Reasoning

Must NOT:

* Store embeddings
* Parse documents
* Manage document storage

### Leadgen API

Role:

* Knowledge Base Service

Responsibilities:

* Document ingestion
* Document parsing
* Chunk generation
* Embedding generation
* Semantic search
* Metadata management

### MinIO

Role:

* Object Storage

Stores:

* PDF
* PPTX
* DOCX
* Original source files

Bucket:

* leadgen-docs

### PostgreSQL + pgvector

Role:

* Search Layer

Stores:

* document metadata
* ingestion jobs
* chunks
* embeddings

Tables:

* documents
* document_chunks
* ingestion_jobs

## Future Subagents

### Doc Librarian

Responsibilities:

* Search documents
* Retrieve sources
* Manage metadata

### Lead Analyst

Responsibilities:

* Match opportunities
* Find relevant case studies
* Build lead context

### Ingestion Agent

Responsibilities:

* Trigger indexing
* Monitor ingestion jobs

## Design Principles

1. OpenClaw is the brain.
2. Leadgen API is the execution layer.
3. MinIO stores originals.
4. Postgres stores searchable knowledge.
5. All integrations go through APIs/tools.
6. Services communicate through Docker network leadgen_net.
