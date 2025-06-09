import os
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

# Load environment variables from .env file
load_dotenv()

class Config(BaseSettings):
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    gmail_client_id: str = Field(..., env="GMAIL_CLIENT_ID")
    gmail_client_secret: str = Field(..., env="GMAIL_CLIENT_SECRET")
    gmail_refresh_token: str = Field(..., env="GMAIL_REFRESH_TOKEN")
    langgraph_env: str = Field("development", env="LANGGRAPH_ENV")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

config = Config()

# Create necessary directories
def create_directories():
    """Create necessary directories for the application."""
    directories = [
        config.memory.procedural_memory_path,
        config.memory.semantic_memory_path,
        config.memory.episodic_memory_path,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Initialize directories
create_directories() 