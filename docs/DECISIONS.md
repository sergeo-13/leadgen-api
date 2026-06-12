# Decisions

## ADR-001

Decision:
Use OpenClaw as orchestration layer only.

Reason:
Keeps business logic separated from storage and ingestion.

---

## ADR-002

Decision:
Store original files in MinIO.

Reason:
Cheap, scalable, S3-compatible storage.

---

## ADR-003

Decision:
Store embeddings in PostgreSQL + pgvector.

Reason:
Simple deployment and sufficient for MVP.

---

## ADR-004

Decision:
Use OpenAI embeddings.

Model:
text-embedding-3-small

Reason:
Good quality/cost ratio.

---

## ADR-005

Decision:
Initial document volume limited to approximately 20 files.

Reason:
Fast MVP validation.

---

## ADR-006

Decision:
Leadgen API acts as the only storage access layer.

Reason:
Prevents OpenClaw from becoming tightly coupled to storage implementation.

---

## ADR-007

Decision:
Single shared Docker network.

Network:
leadgen_net

Reason:
Simple service discovery by container name.

---

## ADR-008

Decision:
Implement health checks before ingestion logic.

Reason:
Infrastructure must be verified before feature development.

---

## ADR-009

Decision:
Do not use IVFFlat pgvector index for MVP.

Reason:
The project currently has a small number of document chunks. Creating an IVFFlat index too early, especially with lists=100 on a tiny dataset, caused semantic search to return empty results despite valid embeddings. For MVP, exact vector search is fast enough and more reliable.

Current state:
document_chunks_embedding_idx was dropped.

SQL:
```sql
DROP INDEX IF EXISTS document_chunks_embedding_idx;
```

Future:
Reintroduce vector index only when the dataset grows significantly, and tune lists/probes based on actual chunk count.

