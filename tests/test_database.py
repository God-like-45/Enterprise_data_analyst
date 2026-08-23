from app.database.connection import db_manager

def test_successful_query():
    # Query the seed data we inserted in Phase 2
    query = "SELECT first_name, email FROM customers WHERE country = 'USA';"
    result = db_manager.execute_query(query)
    
    assert result["success"] is True
    assert result["row_count"] >= 1
    assert "columns" in result
    assert "first_name" in result["columns"]
    # Ensure Alice is in the results
    assert any(row["first_name"] == "Alice" for row in result["rows"])

def test_blocked_query():
    # Prove that our application layer blocks destructive commands
    query = "DROP TABLE customers;"
    result = db_manager.execute_query(query)
    
    assert result["success"] is False
    assert "Security" in result["error"]

def test_sql_syntax_error():
    # Prove that invalid SQL is caught and returns a graceful error dictionary
    query = "SELECT * FROM nonexistent_table;"
    result = db_manager.execute_query(query)
    
    assert result["success"] is False
    assert "does not exist" in result["error"]