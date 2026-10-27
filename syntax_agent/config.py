"""Configuration and settings for SyntaxFixer AI Agent."""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

# Load .env if present
load_dotenv()


class AgentConfig(BaseModel):
    """Global configuration for SyntaxFixer AI Agent."""
    
    # LLM Provider settings
    default_provider: str = Field(
        default_factory=lambda: os.getenv("SYNTAX_AGENT_PROVIDER", "gemini").lower()
    )
    gemini_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    )
    
    openai_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    openai_base_url: str = Field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    openai_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )
    
    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5-coder")
    )
    
    # GitHub Settings
    github_token: Optional[str] = Field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    )
    
    # Agent behavior
    max_reflection_retries: int = Field(default=3)
    temperature: float = Field(default=0.1)  # Low temperature for deterministic code fixes
    
    # Scanner ignore patterns
    ignored_directories: List[str] = Field(
        default_factory=lambda: [
            ".git",
            "node_modules",
            "venv",
            ".venv",
            "env",
            ".env",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "dist",
            "build",
            ".idea",
            ".vscode",
            ".next",
            ".nuxt",
            "coverage",
            "site-packages",
        ]
    )
    
    # File extensions supported
    supported_extensions: List[str] = Field(
        default_factory=lambda: [
            ".py",
            ".js",
            ".mjs",
            ".cjs",
            ".json",
            ".yaml",
            ".yml",
        ]
    )


# Singleton instance
settings = AgentConfig()
