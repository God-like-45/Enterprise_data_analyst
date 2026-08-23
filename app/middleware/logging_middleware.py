import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.logger import setup_logger

logger = setup_logger("request_logger")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Attach request ID for tracking
        request.state.request_id = request_id
        
        logger.info(f"[{request_id}] Incoming {request.method} request to {request.url.path}")
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            
            logger.info(
                f"[{request_id}] Completed {request.method} {request.url.path} "
                f"Status: {response.status_code} | Latency: {process_time:.2f}ms"
            )
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
            return response
            
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(f"[{request_id}] Failed {request.method} {request.url.path} after {process_time:.2f}ms. Error: {str(e)}")
            raise e