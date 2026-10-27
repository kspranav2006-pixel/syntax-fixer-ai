"""Agent package for syntax error correction."""

from syntax_agent.agent.prompts import SYNTAX_FIXER_SYSTEM_PROMPT, build_repair_user_prompt
from syntax_agent.agent.providers import (
    BaseLLMProvider,
    GeminiProvider,
    OpenAIProvider,
    OllamaProvider,
    HeuristicProvider,
    get_provider,
)
from syntax_agent.agent.repair_agent import SyntaxRepairAgent, RepairResult, RepairAttempt

__all__ = [
    "SYNTAX_FIXER_SYSTEM_PROMPT",
    "build_repair_user_prompt",
    "BaseLLMProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "HeuristicProvider",
    "get_provider",
    "SyntaxRepairAgent",
    "RepairResult",
    "RepairAttempt",
]
