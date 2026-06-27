# REST and MCP API Reference

This document provides a detailed description of the HTTP API endpoints exposed by `leadgen-api`, including request parameters, JSON payloads, and response schemas.

---

## Base Configuration & Context
All REST API routes are prefixed with `/api/v1` except for the health check and internal admin UI routes which are also exposed at the root level.
All request and response models are serialized as standard JSON unless otherwise noted (e.g., multipart file uploads).

---

## Health and Info Endpoints

### 1. API Metadata
Returns public application metadata.

* **Path**: `/api/v1/info`
* **Method**: `GET`
* **Authentication**: None
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  {
    "name": "Leadgen API",
    "version": "0.1.1"
  }
  ```

### 2. Health Status
Verifies connectivity to PostgreSQL and MinIO, and ensures the default storage bucket exists.

* **Path**: `/health` (also mounted at `/api/v1/health`)
* **Method**: `GET`
* **Authentication**: None
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  {
    "status": "ok",
    "postgres": "ok",
    "minio": "ok",
    "version": "0.1.1"
  }
  ```

---

## Document Management Endpoints

### 1. Upload Source Document
Uploads a document file to MinIO, registers its metadata in PostgreSQL, and enqueues/processes it.

* **Path**: `/api/v1/documents/upload`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`
* **Form Parameters**:
  * `file`: (File, Required) The document file (supported formats: `.pdf`, `.txt`, `.md`, `.markdown`, `.csv`, `.docx`, `.xlsx`).
  * `title`: (String, Required) Title of the document.
  * `type`: (String, Required) Category or document type (e.g., `case`, `proposal`).
  * `client_name`: (String, Optional) Client name. Default: `""`.
  * `industry`: (String, Optional) Industry classification. Default: `""`.
  * `geography`: (String, Optional) Geographical scope. Default: `""`.
  * `use_case`: (String, Optional) Specific use case. Default: `""`.
  * `tags`: (String, Optional) Comma-separated list of tags. Default: `""`.
  * `authors`: (String, Optional) Comma-separated list of authors. Default: `""`.
  * `description`: (String, Optional) Short description. Default: `null`.
  * `source_type`: (String, Optional) Origin source type. Default: `null`.
  * `source_url`: (String, Optional) Origin URL if applicable. Default: `null`.
  * `metadata`: (JSON String, Optional) Custom JSON metadata object. Default: `null`.
  * `process_immediately`: (Boolean, Optional) If `true`, runs the text extraction, chunking, and embedding generation synchronously and returns the number of chunks created. Default: `true`.
* **Response Status**: `201 Created`
* **Response Schema (process_immediately=true)**:
  ```json
  {
    "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "job_id": "9a9a3b61-42e1-4c12-87db-bc019a28b0cb",
    "status": "completed",
    "source_object_key": "leadgen_case_study.pdf",
    "source_bucket": "leadgen-docs",
    "chunks_created": 12
  }
  ```
* **Response Schema (process_immediately=false)**:
  ```json
  {
    "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "job_id": "9a9a3b61-42e1-4c12-87db-bc019a28b0cb",
    "status": "uploaded",
    "source_object_key": "leadgen_case_study.pdf",
    "source_bucket": "leadgen-docs",
    "chunks_created": null
  }
  ```

### 2. Ingest Metadata
Registers a document whose source file is already uploaded to MinIO and schedules a pending ingestion job.

* **Path**: `/api/v1/documents/ingest`
* **Method**: `POST`
* **Content-Type**: `application/json`
* **Request Body**:
  ```json
  {
    "object_key": "raw_files/historical_overview.txt",
    "title": "Historical Overview Document",
    "metadata": {
      "type": "case",
      "client_name": "Initech",
      "industry": "Finance",
      "geography": "North America",
      "use_case": "Risk Assessment",
      "tags": ["financial", "overview"],
      "authors": ["Analyst A"],
      "description": "Internal assessment summary",
      "source_type": "internal",
      "source_url": null,
      "metadata": {}
    }
  }
  ```
* **Response Status**: `201 Created`
* **Response Schema**:
  ```json
  {
    "document_id": "a576dbb0-8f92-4fdb-ac49-3738e4a9ab71",
    "job_id": "ee025b68-e4b2-4d10-85f0-bd4467d329ee",
    "status": "pending"
  }
  ```

### 3. List Documents
Returns all registered documents along with their computed chunk counts.

* **Path**: `/api/v1/documents`
* **Method**: `GET`
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  [
    {
      "id": "a576dbb0-8f92-4fdb-ac49-3738e4a9ab71",
      "title": "Historical Overview Document",
      "type": "case",
      "client_name": "Initech",
      "industry": "Finance",
      "geography": "North America",
      "use_case": "Risk Assessment",
      "tags": ["financial", "overview"],
      "authors": ["Analyst A"],
      "source_bucket": "leadgen-docs",
      "source_object_key": "raw_files/historical_overview.txt",
      "status": "processed",
      "confidentiality_level": "internal",
      "created_at": "2026-06-25T10:00:00Z",
      "updated_at": "2026-06-25T10:05:00Z",
      "description": "Internal assessment summary",
      "source_type": "internal",
      "source_url": null,
      "file_name": "historical_overview.txt",
      "mime_type": "text/plain",
      "file_size": 10452,
      "metadata": {},
      "chunk_count": 4
    }
  ]
  ```

### 4. Get Document Details
Retrieves details for a single document.

* **Path**: `/api/v1/documents/{document_id}`
* **Method**: `GET`
* **Response Status**: `200 OK`
* **Response Schema**: Similar to a single object in the **List Documents** response.

### 5. Update Metadata
Updates document metadata in the database.
> [!NOTE]
> This is a metadata-only edit and does **NOT** trigger a search index rebuild or re-ingest.

* **Path**: `/api/v1/documents/{document_id}`
* **Method**: `PATCH`
* **Content-Type**: `application/json`
* **Request Parameters**:
  * `title`: (Query parameter, String, Required) Updated title.
* **Request Body** (DocumentMetadata payload):
  ```json
  {
    "type": "case",
    "client_name": "Initech Corp",
    "industry": "Finance",
    "geography": "North America",
    "use_case": "Risk Mitigation",
    "tags": ["financial", "v2"],
    "authors": ["Analyst A", "Analyst B"],
    "description": "Updated assessment summary",
    "source_type": "internal",
    "source_url": "https://internal.site/doc",
    "file_name": "historical_overview.txt",
    "mime_type": "text/plain",
    "file_size": 10452,
    "metadata": {
      "reviewed_by": "Compliance"
    }
  }
  ```
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  {
    "status": "success",
    "message": "Document metadata updated successfully."
  }
  ```

### 6. Rebuild Search Index
Manually enqueues or processes a new job to parse, chunk, and embed the document's *existing* source file.
> [!WARNING]
> This operation is blocked if the document is archived. Restore it first.

* **Path**: `/api/v1/documents/{document_id}/reingest`
* **Method**: `POST`
* **Content-Type**: `application/json`
* **Request Body**:
  ```json
  {
    "reason": "Regenerating embeddings with fine-tuned model settings",
    "process_immediately": true
  }
  ```
* **Response Status**: `201 Created`
* **Response Schema**:
  ```json
  {
    "document_id": "a576dbb0-8f92-4fdb-ac49-3738e4a9ab71",
    "job_id": "b1b1c2c2-d3d4-e5e6-f7f8-09090a0a0b0b",
    "status": "completed"
  }
  ```

### 7. Replace Source File
Uploads a new source file version to MinIO under a timestamped unique key (preserving history) and enqueues a rebuild of the index.

* **Path**: `/api/v1/documents/{document_id}/replace-file`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`
* **Form Parameters**:
  * `file`: (File, Required) The replacement file.
  * `process_immediately`: (Boolean, Optional) Default: `true`.
* **Response Status**: `201 Created`
* **Response Schema**:
  ```json
  {
    "document_id": "a576dbb0-8f92-4fdb-ac49-3738e4a9ab71",
    "job_id": "8c8c9d9d-e0e0-f1f1-a2a2-b3b3b4b4b5b5",
    "status": "completed",
    "source_object_key": "documents/a576dbb0-8f92-4fdb-ac49-3738e4a9ab71/versions/1719321234_new_overview.txt",
    "source_bucket": "leadgen-docs",
    "chunks_created": 5
  }
  ```

### 8. Archive Document
Soft-deletes a document. Sets its status to `'archived'` and removes it from semantic search indices.

* **Path**: `/api/v1/documents/{document_id}/archive`
* **Method**: `POST`
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  {
    "status": "success",
    "message": "Document 'a576dbb0-8f92-4fdb-ac49-3738e4a9ab71' archived successfully."
  }
  ```

### 9. Restore Document
Restores an archived document. If chunks are already present in the database, it resets its status to `'processed'`; otherwise, sets it to `'uploaded'`.

* **Path**: `/api/v1/documents/{document_id}/restore`
* **Method**: `POST`
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  {
    "status": "success",
    "message": "Document 'a576dbb0-8f92-4fdb-ac49-3738e4a9ab71' restored successfully.",
    "document_status": "processed"
  }
  ```

### 10. Get Document Jobs
Retrieves all ingestion and index job history associated with this document.

* **Path**: `/api/v1/documents/{document_id}/jobs`
* **Method**: `GET`
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  [
    {
      "id": "8c8c9d9d-e0e0-f1f1-a2a2-b3b3b4b4b5b5",
      "document_id": "a576dbb0-8f92-4fdb-ac49-3738e4a9ab71",
      "source_bucket": "leadgen-docs",
      "source_object_key": "documents/a576dbb0-8f92-4fdb-ac49-3738e4a9ab71/versions/1719321234_new_overview.txt",
      "status": "completed",
      "error": null,
      "created_at": "2026-06-25T10:05:00Z",
      "updated_at": "2026-06-25T10:06:00Z"
    }
  ]
  ```

### 11. Semantic Search
Performs vector semantic search against chunk text using OpenAI embeddings and pgvector.
> [!NOTE]
> Results are restricted strictly to documents whose status is `'processed'`.

* **Path**: `/api/v1/documents/search`
* **Method**: `POST`
* **Content-Type**: `application/json`
* **Request Body**:
  ```json
  {
    "query": "What are our risk mitigation processes?",
    "limit": 5,
    "filters": {
      "type": "case",
      "client_name": "Initech Corp",
      "industry": null,
      "geography": null,
      "use_case": null,
      "tags": ["financial"]
    }
  }
  ```
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  {
    "query": "What are our risk mitigation processes?",
    "results": [
      {
        "document_id": "a576dbb0-8f92-4fdb-ac49-3738e4a9ab71",
        "title": "Historical Overview Document",
        "type": "case",
        "client_name": "Initech Corp",
        "industry": "Finance",
        "geography": "North America",
        "use_case": "Risk Mitigation",
        "tags": ["financial", "v2"],
        "authors": ["Analyst A"],
        "source_bucket": "leadgen-docs",
        "source_object_key": "documents/a576dbb0-8f92-4fdb-ac49-3738e4a9ab71/versions/1719321234_new_overview.txt",
        "chunk_id": "c1c1d2d2-e3e4-f5f6-a7a8-b9b9b0b0b1b1",
        "chunk_index": 2,
        "content": "Risk mitigation processes involve structured compliance steps...",
        "score": 0.8932
      }
    ]
  }
  ```

---

## Ingestion Queue & Job Operations

### 1. Process Next Pending Job
Atomic database transaction to claim and run the next pending ingestion job.

* **Path**: `/api/v1/ingestion/process-next`
* **Method**: `POST`
* **Response Status**: `200 OK`
* **Response Schema (if job processed)**:
  ```json
  {
    "status": "completed",
    "job_id": "ee025b68-e4b2-4d10-85f0-bd4467d329ee",
    "document_id": "a576dbb0-8f92-4fdb-ac49-3738e4a9ab71",
    "chunks_created": 4
  }
  ```
* **Response Schema (if queue empty)**:
  ```json
  {
    "status": "no_pending_jobs"
  }
  ```

### 2. List Ingestion Jobs
Queries jobs with pagination.

* **Path**: `/api/v1/ingestion/jobs`
* **Method**: `GET`
* **Query Parameters**:
  * `status`: (String, Optional) Filter by job status (`pending`, `processing`, `completed`, `failed`).
  * `document_id`: (String, Optional) Filter by document UUID.
  * `limit`: (Integer, Optional) Range: `1-100`. Default: `50`.
  * `offset`: (Integer, Optional) Offset index. Default: `0`.
* **Response Status**: `200 OK`

### 3. Get Ingestion Job Details
* **Path**: `/api/v1/ingestion/jobs/{job_id}`
* **Method**: `GET`
* **Response Status**: `200 OK`

### 4. Retry Failed Job
Resets a failed job to `'pending'` and resets the document's status to `'uploaded'`. Optionally processes the job immediately.

* **Path**: `/api/v1/ingestion/jobs/{job_id}/retry`
* **Method**: `POST`
* **Query Parameters**:
  * `process_immediately`: (Boolean, Optional) Default: `true`.
* **Response Status**: `200 OK`

---

## Programmatic Hermes Integration Endpoints
These endpoints are thin HTTP client wrappers that delegate queries directly to the external **Hermes Gateway**.

### 1. Send Test Message to Hermes
Forwards a text message to the internal Hermes gateway completions API.

* **Path**: `/api/v1/hermes/test-message`
* **Method**: `POST`
* **Content-Type**: `application/json`
* **Request Body**:
  ```json
  {
    "session_key": "test-session-123",
    "message": "Verify the agent connectivity."
  }
  ```
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  {
    "session_key": "test-session-123",
    "model": "hermes-agent",
    "response": "Hermes connection is verified and operational.",
    "raw": {
      "id": "chatcmpl-...",
      "object": "chat.completion",
      "created": 1719321300,
      "model": "hermes-agent",
      "choices": [
        {
          "index": 0,
          "message": {
            "role": "assistant",
            "content": "Hermes connection is verified and operational."
          },
          "finish_reason": "stop"
        }
      ]
    }
  }
  ```

### 2. Check Hermes Gateway Reachability
Verifies if leadgen-api can connect to the internal Hermes gateway endpoint.

* **Path**: `/api/v1/hermes/health`
* **Method**: `GET`
* **Response Status**: `200 OK`
* **Response Schema**:
  ```json
  {
    "status": "ok"
  }
  ```

---

## Model Context Protocol (MCP) Endpoint

Exposes semantic search capabilities as a stateless tool to compatible agent environments.

* **Path**: `/mcp`
* **Method**: `POST`
* **Authentication**: Enforced `Bearer <mcp_api_key>` token in the `Authorization` header (if `MCP_API_KEY` is configured).
* **Protocol**: Model Context Protocol over stateless HTTP.
* **Server State**: Initialized in `stateless` mode (`stateless_http=True` and `json_response=True` are explicitly set).
* **Supported Tool**: `search_knowledge_base`
  * **Description**: Queries the processed Knowledge Base.
  * **Input Schema**:
    * `query`: (String, Required) Question or search string.
    * `limit`: (Integer, Optional, Range: `1-20`) Maximum relevant chunks to return. Default: `5`.
    * `type`: (String, Optional)
    * `client_name`: (String, Optional)
    * `industry`: (String, Optional)
    * `geography`: (String, Optional)
    * `use_case`: (String, Optional)
    * `tags`: (Array of Strings, Optional)
  * **Response Format**: Returns a JSON structure containing matched chunks, matching scores, and document metadata. Reuses the standard database search service.
