from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Enterprise Data Analyst"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str 
    openai_api_key: str  
    qdrant_url: str = "http://localhost:6333"
    
    # --- NEW VARIABLE ---
    groq_api_key: str
    ui_password: str = "admin"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()