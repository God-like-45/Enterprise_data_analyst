import re
from groq import Groq
from app.config.settings import settings
from app.rag.vector_store import vector_store
from app.database.connection import db_manager
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class SQLAgent:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = "openai/gpt-oss-120b"
        
    def generate_sql(self, question: str, schema_context: str, previous_errors: str = "") -> str:
        """Constructs the prompt, optionally injecting previous errors for self-correction."""
        
        prompt = f"""You are an expert PostgreSQL database architect. 
        Write a SQL query to answer the user's question based STRICTLY on the provided schema.
        
        CRITICAL RULES:
        1. Return ONLY the raw SQL query. 
        2. Do not include markdown formatting like ```sql or ```.
        3. Do not include explanations, greetings, or pleasantries.
        4. If the question cannot be answered using the schema, return exactly: "I do not have the data to answer this."
        
        Schema:
        {schema_context}
        """
        
        # AGENTIC BEHAVIOR: If the LLM failed previously, we tell it exactly why!
        if previous_errors:
            prompt += f"\nPREVIOUS ATTEMPTS FAILED WITH THESE ERRORS. Fix your SQL:\n{previous_errors}\n"
            
        prompt += f"\nQuestion: {question}\n"
        
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a database engine that outputs strictly raw SQL code."},
                {"role": "user", "content": prompt}
            ],
            model=self.model,
            temperature=0.0
        )
        
        raw_output = response.choices[0].message.content.strip()
        clean_sql = re.sub(r'```sql|```', '', raw_output).strip()
        return clean_sql
        
    def answer_question(self, question: str, max_retries: int = 2) -> dict:
        """Executes the self-correcting loop."""
        logger.info(f"User asked: {question}")
        
        # 1. Retrieve context only once to save time
        schema_context = vector_store.retrieve_relevant_tables(question, top_k=4)
        previous_errors = ""
        
        # 2. The Retry Loop
        for attempt in range(max_retries + 1):
            logger.info(f"--- ATTEMPT {attempt + 1} ---")
            
            sql = self.generate_sql(question, schema_context, previous_errors)
            logger.info(f"Generated SQL: \n{sql}")
            
            if sql == "I do not have the data to answer this.":
                return {"success": False, "error": "Out of domain question."}
                
            # Try to run it against Postgres
            result = db_manager.execute_query(sql)
            
            if result["success"]:
                logger.info(f"Query succeeded on attempt {attempt + 1}!")
                return {
                    "question": question,
                    "generated_sql": sql,
                    "database_result": result,
                    "attempts": attempt + 1
                }
            else:
                # Capture the database error and feed it back to the AI on the next loop
                error_msg = result.get("error", "Unknown Database Error")
                logger.warning(f"SQL Execution Failed: {error_msg}")
                previous_errors += f"\nAttempt {attempt + 1} Failed SQL:\n{sql}\nDatabase Error: {error_msg}\n"
                
        # If we exhaust all retries, return a graceful failure
        return {
            "success": False, 
            "error": f"AI failed to write a valid query after {max_retries + 1} attempts."
        }

# Singleton instance
sql_agent = SQLAgent()