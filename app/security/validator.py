import re
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class SQLValidator:
    # Use word boundaries (\b) to ensure we don't accidentally block column names 
    # like "update_date" or "drop_off_location"
    FORBIDDEN_OPERATIONS = re.compile(
        r'\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|commit|rollback)\b', 
        re.IGNORECASE
    )

    @classmethod
    def is_safe(cls, query: str) -> tuple[bool, str]:
        """
        Validates that the SQL query is safe to execute.
        Returns a tuple: (is_safe: bool, error_message: str)
        """
        # 1. Block multiple statements (prevents stacked queries SQL injection)
        # We allow a single trailing semicolon, but no semicolons in the middle
        stripped_query = query.strip()
        if ';' in stripped_query[:-1]:
            logger.warning(f"Blocked multiple SQL statements: {query}")
            return False, "Security Error: Multiple SQL statements are not allowed."

        # 2. Block forbidden DML/DDL commands
        if cls.FORBIDDEN_OPERATIONS.search(query):
            logger.warning(f"Blocked destructive SQL command: {query}")
            return False, "Security Error: Data modification commands are strictly prohibited."

        return True, ""