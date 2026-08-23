from fastapi import FastAPI, HTTPException
from app.schemas.api import QueryRequest, QueryResponse
from app.agent.sql_agent import sql_agent
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(
    title="Enterprise Data Analyst API",
    description="AI-powered Text-to-SQL backend",
    version="1.0.0"
)
@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}

@app.post("/api/v1/query", response_model=QueryResponse)
def ask_database(request: QueryRequest):
    """Takes a natural language question, generates SQL, and returns the DB results."""
    logger.info(f"API received question: {request.question}")
    
    try:
        # Call the agent
        agent_result = sql_agent.answer_question(request.question)
        
        # 1. NEW: Check if the AI Agent itself rejected the question or ran out of retries
        if "error" in agent_result:
            return QueryResponse(
                success=False,
                question=request.question,
                error=agent_result.get("error")
            )
            
        # 2. Proceed normally if the agent succeeded
        db_result = agent_result.get("database_result", {})
        
        if not db_result.get("success"):
            return QueryResponse(
                success=False,
                question=request.question,
                generated_sql=agent_result.get("generated_sql"),
                error=db_result.get("error", "Database execution failed.")
            )
            
        return QueryResponse(
            success=True,
            question=request.question,
            generated_sql=agent_result.get("generated_sql"),
            data=db_result.get("rows", [])
        )
        
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error processing query.")