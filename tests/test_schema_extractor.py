from app.services.schema_extractor import schema_extractor

def test_extract_tables():
    tables = schema_extractor.extract_schema()
    
    # We should have extracted the tables we created in Phase 2
    assert len(tables) >= 5
    
    table_names = [t.table_name for t in tables]
    assert "customers" in table_names
    assert "orders" in table_names
    assert "order_items" in table_names

def test_extract_foreign_keys():
    tables = schema_extractor.extract_schema()
    
    # Find the orders table
    orders_table = next(t for t in tables if t.table_name == "orders")
    
    # Find the customer_id column in the orders table
    customer_id_col = next(c for c in orders_table.columns if c.name == "customer_id")
    
    # It should correctly identify that it points to the customers table
    assert customer_id_col.foreign_key_target == "customers.customer_id"

def test_llm_string_formatting():
    tables = schema_extractor.extract_schema()
    customers_table = next(t for t in tables if t.table_name == "customers")
    
    llm_string = customers_table.to_llm_string()
    
    # Check that our output string is formatted properly
    assert "Table: customers" in llm_string
    assert "customer_id (INTEGER) (PRIMARY KEY)" in llm_string
    assert "email (VARCHAR(255))" in llm_string