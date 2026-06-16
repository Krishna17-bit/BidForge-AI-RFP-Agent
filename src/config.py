from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    app_mode: str = os.getenv("APP_MODE", "local")
    mock_mode: bool = os.getenv("MOCK_MODE", "true").lower() in ("true", "1", "yes")
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    
    mistral_api_key: str | None = os.getenv("MISTRAL_API_KEY")
    mistral_model: str = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
    
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    
    custom_openai_base_url: str | None = os.getenv("CUSTOM_OPENAI_BASE_URL")
    custom_openai_api_key: str | None = os.getenv("CUSTOM_OPENAI_API_KEY")
    custom_openai_model: str | None = os.getenv("CUSTOM_OPENAI_MODEL")
    
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    max_chars_per_prompt: int = int(os.getenv("MAX_CHARS_PER_PROMPT", "70000"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
    enable_ocr: bool = os.getenv("ENABLE_OCR", "false").lower() in ("true", "1", "yes")
    enable_demo_data: bool = os.getenv("ENABLE_DEMO_DATA", "true").lower() in ("true", "1", "yes")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///bidforge.db")

settings = Settings()
