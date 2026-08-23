from app.agent.sql_agent import sql_agent

def test_agent_generates_and_executes_sql():
    # This requires the AI to figure out how to join the 'customers' table 
    # with the 'orders' table to find out who spent the most money.
    question = "Which customer made the largest single order by total amount? Return their first name and the amount."
    
    result = sql_agent.answer_question(question)
    
    # Verify the pipeline didn't crash
    assert "generated_sql" in result
    assert result["database_result"]["success"] is True
    assert result["database_result"]["row_count"] > 0
    
    print("\n--- AI AGENT RESULTS ---")
    print(f"Generated SQL:\n{result['generated_sql']}\n")
    print(f"Data Retrieved from Postgres: {result['database_result']['rows']}")