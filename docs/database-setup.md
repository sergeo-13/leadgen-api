# Database Setup Guide

This guide details how to configure, update, and manage the PostgreSQL database containing `pgvector` extension for your Leadgen API deployment.

---

## Connecting to PostgreSQL on VPS

The database runs in a Docker container named `leadgen-postgres`. To connect directly to the container and open the `psql` interactive terminal, execute:

```bash
docker exec -it leadgen-postgres psql -U leadgen -d leadgen
```

---

## Initial Setup (if needed)

If the database or user does not exist yet:

1. Open the PostgreSQL container's superuser shell:
   ```bash
   docker exec -it leadgen-postgres psql -U postgres
   ```
2. Create the user and database with the required privileges:
   ```sql
   CREATE USER leadgen WITH PASSWORD 'your_secure_password';
   CREATE DATABASE leadgen OWNER leadgen;
   GRANT ALL PRIVILEGES ON DATABASE leadgen TO leadgen;
   ```
3. Exit `psql`:
   ```sql
   \q
   ```

---

## Backing Up Existing Data

> [!WARNING]
> Always run a full backup of the production database before applying any schema migrations or executing new SQL scripts.

```bash
docker exec -t leadgen-postgres pg_dump -U leadgen -d leadgen > backup_$(date +%F).sql
```

---

## Applying Schema & Migrations

To apply the idempotent schema configuration in [schema.sql](schema.sql):

### Option A: Piping directly (Recommended)
```bash
cat docs/schema.sql | docker exec -i leadgen-postgres psql -U leadgen -d leadgen
```

### Option B: Copying the file first
```bash
docker cp docs/schema.sql leadgen-postgres:/tmp/schema.sql
docker exec -it leadgen-postgres psql -U leadgen -d leadgen -f /tmp/schema.sql
```

---

## Verifying the Setup

After executing `schema.sql`, connect to the database and verify:

1. **Verify tables exist:**
   ```sql
   \dt
   ```
   You should see:
   - `documents`
   - `ingestion_jobs`
   - `document_chunks`

2. **Verify table structure:**
   Check the columns of `documents` to confirm the fields are present:
   ```sql
   \d documents
   ```

3. **Verify the `vector` extension is active:**
   ```sql
   SELECT extname, nspname, extversion FROM pg_extension WHERE extname = 'vector';
   ```

---

## Environments Note
By default, the development and production environments may share the same database instance unless they are configured with separate database names or hosts in their respective environment files/compose definitions. Ensure you separate them if you require isolated test datasets.
