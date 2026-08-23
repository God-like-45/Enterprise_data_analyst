from pydantic import BaseModel
from typing import Any

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    success: bool
    question: str
    generated_sql: str | None = None
    data: list[dict[str, Any]] | None = None
    error: str | None = None