import os
import pathlib
import psycopg2

# The admin URL is used for schema creation, seeding, and role setup.
# Falls back to DATABASE_URL for backwards compatibility (local dev).
ADMIN_DATABASE_URL = os.getenv(
    "ADMIN_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://ai_analyst:ai_secure_pass_123@localhost:5432/enterprise_db")
)

# The app-level URL used by the AI analyst (read-only role).
APP_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ai_analyst:ai_secure_pass_123@localhost:5432/enterprise_db"
)

SCRIPTS_DIR = pathlib.Path(__file__).parent


def _read_sql_file(filename: str) -> str:
    """Reads a SQL file from the scripts directory."""
    filepath = SCRIPTS_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def initialize_database():
    print(f"Connecting to database with admin URL...")
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(ADMIN_DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        # --- Step 1: Drop existing tables for a clean slate ---
        print("Dropping existing tables...")
        cursor.execute(
            "DROP TABLE IF EXISTS payments, order_items, orders, customers, "
            "products, categories, employees CASCADE;"
        )

        # --- Step 2: Create tables from the authoritative SQL file ---
        print("Creating tables from 01_schema.sql...")
        schema_sql = _read_sql_file("01_schema.sql")
        cursor.execute(schema_sql)

        # --- Step 3: Insert seed data from the authoritative SQL file ---
        print("Inserting seed data from 02_seed.sql...")
        seed_sql = _read_sql_file("02_seed.sql")
        cursor.execute(seed_sql)

        print("✅ Database schema and seed data initialized successfully!")

        # --- Step 4: Set up read-only role ---
        # Only create the role if we're running as a superuser (admin),
        # not if we're already connected as ai_analyst.
        try:
            # Check if ai_analyst role already exists
            cursor.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = 'ai_analyst';"
            )
            role_exists = cursor.fetchone() is not None

            # Get the current user to check if we need role setup
            cursor.execute("SELECT current_user;")
            current_user = cursor.fetchone()[0]

            if current_user != "ai_analyst":
                if not role_exists:
                    print("Creating read-only ai_analyst role...")
                    cursor.execute(
                        "CREATE ROLE ai_analyst WITH LOGIN PASSWORD 'secure_password_123';"
                    )
                else:
                    print("Role ai_analyst already exists, updating permissions...")

                # Grant read-only permissions
                cursor.execute(
                    "GRANT CONNECT ON DATABASE enterprise_db TO ai_analyst;"
                )
                cursor.execute(
                    "GRANT USAGE ON SCHEMA public TO ai_analyst;"
                )
                cursor.execute(
                    "GRANT SELECT ON ALL TABLES IN SCHEMA public TO ai_analyst;"
                )
                cursor.execute(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "GRANT SELECT ON TABLES TO ai_analyst;"
                )
                # Explicitly revoke any write permissions
                cursor.execute(
                    "REVOKE INSERT, UPDATE, DELETE, TRUNCATE "
                    "ON ALL TABLES IN SCHEMA public FROM ai_analyst;"
                )
                print("✅ Read-only role configured successfully!")
            else:
                print("Running as ai_analyst — skipping role setup.")

        except Exception as role_err:
            print(f"⚠️ Role setup warning (non-fatal): {role_err}")

        # --- Step 5: Populate Qdrant vector store ---
        print("Waiting for Qdrant to be ready...")
        import time
        import requests
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        for i in range(15):
            try:
                # Check Qdrant readiness
                response = requests.get(f"{qdrant_url}/collections", timeout=2)
                if response.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Qdrant failed to start in time.")

        print("Populating Qdrant Vector Store...")
        # Set DATABASE_URL to the app URL so schema extractor uses the right connection
        os.environ["DATABASE_URL"] = APP_DATABASE_URL

        from app.services.schema_extractor import schema_extractor
        from app.rag.vector_store import vector_store

        tables = schema_extractor.extract_schema()
        vector_store.index_schema(tables)  # Fixed: was store_schema()
        print(f"✅ Qdrant populated with {len(tables)} tables successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    initialize_database()