-- Enable vector and pgcrypto extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Documents Table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    type TEXT,
    client_name TEXT,
    industry TEXT,
    geography TEXT,
    use_case TEXT,
    tags TEXT[] DEFAULT '{}',
    authors TEXT[] DEFAULT '{}',
    source_bucket TEXT NOT NULL,
    source_object_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded',
    confidentiality_level TEXT DEFAULT 'internal',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ingestion Jobs Table
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_bucket TEXT NOT NULL,
    source_object_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document Chunks Table
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL
);

-- Indices
CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx ON document_chunks(document_id);

-- Safe Generic Columns Additions
ALTER TABLE documents ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_type TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_name TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size BIGINT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Safe status migration of existing document statuses
-- 1. If documents have chunks with non-null embeddings, set status to 'processed'
UPDATE documents d
SET status = 'processed', updated_at = NOW()
WHERE status = 'active'
  AND EXISTS (
    SELECT 1
    FROM document_chunks c
    WHERE c.document_id = d.id
      AND c.embedding IS NOT NULL
  );

-- 2. If documents do not have chunks with non-null embeddings, set status to 'uploaded'
UPDATE documents d
SET status = 'uploaded', updated_at = NOW()
WHERE status = 'active'
  AND NOT EXISTS (
    SELECT 1
    FROM document_chunks c
    WHERE c.document_id = d.id
      AND c.embedding IS NOT NULL
  );

-- Auth Login Transactions Table
CREATE TABLE IF NOT EXISTS auth_login_transactions (
    state_hash TEXT PRIMARY KEY,
    msal_flow JSONB NOT NULL,
    return_to TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS auth_login_transactions_expires_at_idx ON auth_login_transactions(expires_at);
