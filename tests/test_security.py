import os
import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database.connection import db_manager
from app.security.validator import SQLValidator

def test_validator_blocks_dml():
    # Application layer should block this
    is_safe, error = SQLValidator.is_safe("DELETE FROM customers WHERE customer_id = 1;")
    assert not is_safe
    assert "Data modification" in error

def test_validator_allows_safe_words():
    # Should NOT block if a forbidden word is part of a column name
    is_safe, _ = SQLValidator.is_safe("SELECT drop_off_time FROM rides;")
    assert is_safe

def test_validator_blocks_multiple_statements():
    # Application layer should block multiple statements
    is_safe, error = SQLValidator.is_safe("SELECT * FROM customers; DROP TABLE orders;")
    assert not is_safe
    assert "Multiple SQL statements" in error
@pytest.mark.skipif(os.getenv("GITHUB_ACTIONS")== "true", reason="CI uses a superuser for a DB steup")
def test_database_role_is_read_only():
    # We bypass the Python validator entirely by using the raw SQLAlchemy engine
    # to prove that the database itself rejects modifications.
    sneaky_query = "DELETE FROM customers;"
    
    try:
        with db_manager.engine.connect() as connection:
            connection.execute(text(sneaky_query))
            connection.commit()
        # If it reaches this line, the test fails because the DB allowed a delete
        assert False, "Security Alert: Database allowed a DELETE operation!"
    except SQLAlchemyError as e:
        # The database itself MUST reject this because 'ai_analyst' lacks permissions
        error_msg = str(e.__dict__.get('orig', e)).lower()
        assert "permission denied" in error_msg