# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.schemas.api import QueryRequest, QueryResponse
from app.agent.sql_agent import sql_agent
from app.config.settings import settings
from app.utils.logger import setup_logger
from app.middleware.logging_middleware import LoggingMiddleware

logger = setup_logger(__name__)

# 1. Initialize the Rate Limiter (tracks requests by remote client IP)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Enterprise Data Analyst API",
    description="AI-powered Text-to-SQL backend with rate limiting and logging telemetry",
    version="1.0.0"
)

# 2. Bind the limiter and register the logging telemetry middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(LoggingMiddleware)

@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "environment": settings.environment}

@app.post("/api/v1/query", response_model=QueryResponse)
@limiter.limit("5/minute")  # 3. Restrict endpoint usage to 5 requests per minute per IP
def ask_database(request: Request, body: QueryRequest):
    """Takes a natural language question, generates SQL, and returns the DB results."""
    logger.info(f"API received question: {body.question}")
    
    try:
        # Call the agent
        agent_result = sql_agent.answer_question(body.question)
        
        # Check if the AI Agent itself rejected the question or ran out of retries
        if "error" in agent_result:
            return QueryResponse(
                success=False,
                question=body.question,
                error=agent_result.get("error")
            )
            
        # Proceed normally if the agent succeeded
        db_result = agent_result.get("database_result", {})
        
        if not db_result.get("success"):
            return QueryResponse(
                success=False,
                question=body.question,
                generated_sql=agent_result.get("generated_sql"),
                error=db_result.get("error", "Database execution failed.")
            )
            
        return QueryResponse(
            success=True,
            question=body.question,
            generated_sql=agent_result.get("generated_sql"),
            data=db_result.get("rows", [])
        )
        
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error processing query.")