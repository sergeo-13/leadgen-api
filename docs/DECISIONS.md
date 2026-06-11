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
