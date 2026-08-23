import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.config.settings import settings
from app.utils.logger import setup_logger
from app.security.validator import SQLValidator

logger = setup_logger(__name__)

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(
            settings.database_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
        )
        logger.info("Database connection pool initialized.")

    def execute_query(self, query: str, timeout_ms: int = 5000) -> dict:
        """Executes a read-only SQL query with validation and strict timeout."""
        
        # 1. Application-Level Security Validation
        is_safe, error_msg = SQLValidator.is_safe(query)
        if not is_safe:
            return {"success": False, "error": error_msg}

        # 2. Execution
        try:
            start_time = time.time()
            with self.engine.connect() as connection:
                connection.execute(text(f"SET statement_timeout = {timeout_ms}"))
                result = connection.execute(text(query))
                
                rows = [dict(row._mapping) for row in result]
                columns = list(result.keys()) if result.returns_rows else []
                execution_time = (time.time() - start_time) * 1000

                return {
                    "success": True,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "execution_time_ms": round(execution_time, 2)
                }
                
        except SQLAlchemyError as e:
            error_msg = str(e.__dict__.get('orig', e))
            logger.error(f"Database execution error: {error_msg}")
            return {"success": False, "error": error_msg}

db_manager = DatabaseManager()