from app.services.schema_extractor import schema_extractor
from app.rag.vector_store import vector_store

def test_rag_pipeline():
    # 1. Extract the latest schema from Postgres
    tables = schema_extractor.extract_schema()
    assert len(tables) > 0
    
    # 2. Index the schema into Qdrant (Calls OpenAI Embeddings API)
    vector_store.index_schema(tables)
    
    # 3. Test Semantic Search
    # If I ask about "purchases" and "buying things", the vector math should 
    # understand that this means the "orders" table, even if the word "order" isn't used!
    question = "Who made the biggest purchase?"
    
    relevant_schema_text = vector_store.retrieve_relevant_tables(question, top_k=4)
    
    # Ensure it pulled the relevant tables
    assert "Table: orders" in relevant_schema_text
    
    print("\n--- Retrieved Context for LLM ---")
    print(relevant_schema_text)