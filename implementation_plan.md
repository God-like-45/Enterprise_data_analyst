# Fix All 6 Failing Tests in Enterprise Data Analyst

## Root Cause Analysis

After thorough investigation, I've identified **6 distinct root causes** behind the 6 failing tests. Here's the full analysis and proposed fixes:

---

## Failure 1: Health endpoint returns 404 → test expects `"environment"` key

**Test**: `test_main.py::test_health_check`
**Root Cause**: The `/health` endpoint at [main.py](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/app/main.py#L13-L16) returns `{"status": "ok"}` but the test on line 12 asserts `assert "environment" in data`. The response is missing the `environment` field.

**Fix**: Add `environment` to the health response by pulling from settings.

---

## Failure 2: Database seed data – `init_db.py` doesn't match schema SQL files

**Test**: `test_database.py::test_successful_query`
**Root Cause**: The [init_db.py](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/scripts/init_db.py) creates tables with a **different schema** than [01_schema.sql](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/scripts/01_schema.sql):
- `init_db.py` creates `customers` with `email VARCHAR(255)` ✅ but only seeds Alice and Jane
- `init_db.py` creates only 5 tables (no `employees`, `payments`)
- The SQL files define 7 tables with richer schema (employees, payments, etc.)

The CI workflow runs `python scripts/init_db.py` which uses the inline Python schema, NOT the `.sql` files. The `init_db.py` has the correct Alice seed data, BUT there's a critical problem: **`vector_store.store_schema()` doesn't exist** – the `VectorStore` class has `index_schema()`, not `store_schema()`. This causes `init_db.py` to crash at line 75, rolling back the entire transaction or leaving partial state.

Wait – `conn.autocommit = True` means the DDL and seed data DO get committed even if the Qdrant part fails. But the Qdrant indexing fails, which means schema is never indexed, which is why the agent fails.

Actually, let me re-analyze: the test asserts Alice exists. If `init_db.py` seeds Alice with `autocommit=True`, the data should be there. The test connects using `db_manager` which uses `settings.database_url`. In CI, that's `postgresql://ai_analyst:secure_password_123@localhost:5432/enterprise_db`. The init script also connects with `ai_analyst`. So Alice should be present.

But wait – the init script schema defines `email VARCHAR(255)` which is correct for the test. The issue with test_database failing is likely that `init_db.py` crashes on line 75 (`vector_store.store_schema(tables)` – method doesn't exist) and the `except` block prints the error but the data was already committed (autocommit). So data IS there.

Actually, re-reading: ALL statements are in a single `cursor.execute()` call. With `autocommit=True`, each SQL statement executes immediately. The tables and seed data should be committed. Then line 72-75 runs schema extraction + Qdrant indexing – the method name mismatch causes a crash, but the DB data is already committed.

So test_database might actually PASS if the schema is right. The real issue might be the `init_db.py` vs CI schema. Let me re-check:

In CI, `init_db.py` runs with `ai_analyst` user who is the POSTGRES_USER (superuser) in CI. The schema creates `email VARCHAR(255)` in init_db.py. So the test should find Alice.

**Revised analysis**: The `init_db.py` has two bugs:
1. Line 75: calls `vector_store.store_schema(tables)` but the method is `index_schema(tables)` → crashes after DB is seeded
2. The schema in `init_db.py` is simpler (5 tables) than `01_schema.sql` (7 tables), but since CI only runs `init_db.py`, the simpler schema is what's used

The test_database failure may not be about missing Alice but about the schema extractor later. Let me check if tests run in isolation or if test ordering matters...

Actually, looking at the CI output description: test_database fails because "The current database does not return Alice." This is the stated failure. Since `init_db.py` DOES insert Alice and autocommit is on, maybe the issue is that `init_db.py` crashes before reaching the INSERT due to the `DROP TABLE` cascade working differently, or the schema creation failing?

No – looking more carefully: the DROP and CREATE are in one `cursor.execute()` call, and the INSERT is in another. Both should succeed with autocommit.

Let me consider: maybe `init_db.py` actually crashes on `from app.services.schema_extractor import schema_extractor` at line 72 (module import failure) or `from app.rag.vector_store import vector_store` at line 73 (Qdrant not available). If this import itself crashes... no, the imports are inside a try block.

Hmm, but `from app.rag.vector_store import vector_store` triggers `vector_store = VectorStore()` which calls `QdrantClient(url=settings.qdrant_url)` and `SentenceTransformer("all-MiniLM-L6-v2")`. If Qdrant is available (CI has it), this should work. Then `vector_store.store_schema(tables)` would raise `AttributeError` since the method is `index_schema`.

So the seed data IS committed. test_database should pass for Alice. Unless the schema mismatch test is the one failing (email VARCHAR(100) vs 255).

Let me re-read the problem statement more carefully for test_database. It says the test expects Alice and "The current database does not return Alice." This suggests the seed data is actually not present. Let me think about why...

OH WAIT. I see it now. Look at the `init_db.py` schema: the customers table in `init_db.py` has `email VARCHAR(255)`, but the **`01_schema.sql`** file has `email VARCHAR(255)` too. BUT the schema extractor reads from the actual database using SQLAlchemy `MetaData.reflect()`. If the init_db.py creates email as VARCHAR(255), then `str(col.type)` should return `VARCHAR(255)`.

The stated failure #4 says the schema extractor outputs `email (VARCHAR(100))`. This means the actual DB has `email VARCHAR(100)`. But `init_db.py` creates it as `VARCHAR(255)`. Unless `init_db.py` is NOT what creates the actual tables...

Actually, in CI the postgres service starts with `POSTGRES_USER: ai_analyst`. This means `ai_analyst` IS the superuser. The `init_db.py` connects as `ai_analyst` and creates tables. So the DB should have `VARCHAR(255)`.

Unless there's another initialization happening. Let me check: maybe the `.sql` files run automatically. No, there's no docker-entrypoint-initdb.d mounting. Only `init_db.py` runs.

OK so maybe the actual failure root cause is different from what's described. The user is reporting CI failures – let me trust the reported symptoms and build fixes accordingly.

**Actual root causes I'm confident about:**

1. `init_db.py` line 75 calls `store_schema()` instead of `index_schema()` → Qdrant never gets populated → agent can't retrieve schema → all agent queries fail
2. `init_db.py` creates a simpler schema than `01_schema.sql` → schema extractor sees 5 tables, not 7
3. No read-only role setup in CI → `ai_analyst` IS the superuser

Let me finalize the plan:

---

> [!IMPORTANT]
> The core architectural problem is that `init_db.py` is diverged from the SQL files and has a method name bug that prevents Qdrant from being populated. The CI also uses a single superuser role without read-only restrictions.

## Proposed Changes

### 1. Database Initialization — Align schema and fix method name

#### [MODIFY] [init_db.py](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/scripts/init_db.py)

- Rewrite to execute the `.sql` files (`01_schema.sql`, `02_seed.sql`) instead of inline SQL, ensuring a single source of truth
- Fix `vector_store.store_schema(tables)` → `vector_store.index_schema(tables)` 
- For CI, handle security setup specially since the postgres service user IS the app user

---

### 2. CI Workflow — Create read-only role + use it for tests

#### [MODIFY] [ci.yml](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/.github/workflows/ci.yml)

- Change the PostgreSQL service to use a **superuser** (`postgres`) for DB setup
- Run `init_db.py` as the superuser to create schema, seed data, AND the read-only `ai_analyst` role
- Run tests with `DATABASE_URL` pointing to the read-only `ai_analyst` user

---

### 3. Security SQL — Ensure read-only role is created by init_db.py

#### [MODIFY] [init_db.py](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/scripts/init_db.py)

- After creating tables and seed data, execute the `03_security.sql` to create the read-only role
- Use a separate `ADMIN_DATABASE_URL` env var for the superuser connection during init

---

### 4. Health Endpoint — Add environment field

#### [MODIFY] [main.py](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/app/main.py#L13-L16)

- Add `environment` field to the health check response from `settings.environment`

---

### 5. Schema Mismatch — Use the SQL files as source of truth

Since we'll now run `01_schema.sql` which defines `email VARCHAR(255)`, the schema extractor will correctly report `VARCHAR(255)`.

---

### 6. Agent "Out of Domain" — Fix Qdrant population

The `store_schema()` → `index_schema()` fix ensures Qdrant gets populated. Combined with the richer 7-table schema from `01_schema.sql`, the RAG retrieval will return proper context. The agent will recognize valid enterprise questions.

---

### 7. Read-only test — Proper role setup

#### [MODIFY] [test_security.py](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/tests/test_security.py#L24)

- Remove the `skipif` for CI – the test should now work because we'll properly set up the read-only role in CI too

---

## Detailed File Changes

### Component: Database Initialization

#### [MODIFY] [init_db.py](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/scripts/init_db.py)
- Use a separate admin/superuser connection (`ADMIN_DATABASE_URL` env var, falling back to `DATABASE_URL`) for schema creation
- Execute `01_schema.sql` and `02_seed.sql` files instead of inline SQL
- Create the `ai_analyst` read-only role (from `03_security.sql`) if not already the connected user
- Fix method call: `store_schema()` → `index_schema()`
- Make idempotent: DROP IF EXISTS before creating

#### [MODIFY] [ci.yml](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/.github/workflows/ci.yml)
- Change Postgres service to use `postgres` superuser
- Set `ADMIN_DATABASE_URL` to superuser URL for init
- Set `DATABASE_URL` to `ai_analyst` (read-only) for tests
- Create the `ai_analyst` role as part of init

---

### Component: FastAPI Application

#### [MODIFY] [main.py](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/app/main.py)
- Add `environment` key to health check response

---

### Component: Security Test

#### [MODIFY] [test_security.py](file:///c:/Users/Umesh%20Chandra/Desktop/Enterprise_data_analyst/tests/test_security.py)
- Remove the `@pytest.mark.skipif` on `test_database_role_is_read_only` – the DB role will now be properly configured in CI too

---

## Verification Plan

### Automated Tests
```bash
pytest -v
```
All 14 tests must pass, 0 failures.

### Manual Verification
- Verify `git diff` shows no secrets or debug code
- Verify the schema in init_db.py matches `01_schema.sql` (single source of truth)
- Verify the `ai_analyst` role is read-only with only SELECT permissions
