# Architectural Decisions Log (ADR)

This document records the architectural decisions made during the design and development of the Leadgen API.

---

## ADR-001: Orchestration Layer Choice

* **Status**: **Superseded** (Historical Reference)
* **Decision**: Use OpenClaw as the orchestration layer only.
* **Reason**: Keep core business logic separate from storage and ingestion services.
* **Hermes Update**: During development, OpenClaw was replaced by the external **Hermes Gateway** and **Hermes WebUI** stack. The principal architecture of separating agent orchestration from database and ingestion logic remains active, with the Hermes stack communicating with the FastAPI service via Model Context Protocol (MCP) tool calls.

---

## ADR-002: Storage Layer for Raw Source Documents

* **Status**: **Active**
* **Decision**: Store original uploaded files in MinIO.
* **Reason**: Provides cheap, scalable, S3-compatible object storage.

---

## ADR-003: Vector Database Selection

* **Status**: **Active**
* **Decision**: Store document chunks and embeddings in PostgreSQL using the `pgvector` extension.
* **Reason**: Minimizes operational footprint by using the same database for structured document metadata, ingestion logs, and vector search. Sufficient for the target volume.

---

## ADR-004: Text Embedding Model

* **Status**: **Active**
* **Decision**: Use OpenAI's `text-embedding-3-small` model.
* **Reason**: Offers a high quality-to-cost ratio and generates 1536-dimensional embeddings.

---

## ADR-005: Dataset Sizing Assumptions

* **Status**: **Historical / Active**
* **Decision**: Scope initial target capacity for approximately 20-100 high-value documents.
* **Reason**: Allows fast validation of retrieval accuracy and agent response grounding before scaling the system.

---

## ADR-006: Data Layer Isolation

* **Status**: **Active**
* **Decision**: leadgen-api acts as the sole access layer for document storage and search.
* **Reason**: Prevents external orchestration and agent engines (historically OpenClaw, currently the Hermes Gateway) from directly accessing PostgreSQL or MinIO, decoupling database schemas and storage layout from the agent runtime.

---

## ADR-007: Networking and Service Discovery

* **Status**: **Active**
* **Decision**: Connect containers via a single external Docker network (`leadgen_net`).
* **Reason**: Enables clean service discovery by container name (e.g. `leadgen-postgres`, `minio`, `leadgen-api`) on the Hostinger VPS host without exposing internal ports externally.

---

## ADR-008: Inception and Health Check Priority

* **Status**: **Active**
* **Decision**: Implement comprehensive dependency checks in the health check endpoint before developing the ingestion flow.
* **Reason**: Ensures the database and storage services are reachable, avoiding ingestion bugs caused by silent database disconnection.

---

## ADR-009: Vector Index Tuning for MVP

* **Status**: **Active**
* **Decision**: Do not create a pgvector index (like IVFFlat or HNSW) on the embeddings database table for the current dataset volume.
* **Reason**: Creating an index on a table with a small number of records can degrade recall and cause queries to return empty result sets. For dataset sizes below 10,000 chunks, exact nearest-neighbor vector search (using pgvector operator orderings) is fast, reliable, and has 100% recall.
* **Action**:
  ```sql
  DROP INDEX IF EXISTS document_chunks_embedding_idx;
  ```

---

## ADR-010: Server-Rendered Public Login Page with Microsoft Entra

* **Status**: **Active**
* **Decision**: Serve a unified, dark-themed public login page (`/login`) directly from `leadgen-api`, using safe query string status/error mappings, and explicitly avoiding frontend JavaScript applications for authentication state. Logout uses a strict POST form.
* **Reason**: Ensures robust security. Hardcoded error code mappings (e.g., `access_denied` -> generic message) prevent raw OAuth error exposure. A strict POST form for `/auth/logout` respects CSRF policies while reliably clearing the secure cookie session before redirecting to the Microsoft logout endpoint. This eliminates cross-origin complexities and prevents malicious open redirects.
