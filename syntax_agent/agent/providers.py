"""LLM Providers supporting Google Gemini, OpenAI, Ollama, and Heuristic rule fallback."""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional
import httpx
from syntax_agent.config import settings

logger = logging.getLogger(__name__)


def clean_code_fence(text: str) -> str:
    """Strips markdown code fences (```lang ... ```) if returned by the LLM."""
    clean = text.strip()
    if clean.startswith("```"):
        # Match ```lang\n ... \n```
        match = re.match(r"^```[a-zA-Z0-9_\-\.\+]*\r?\n([\s\S]*?)\r?\n```$", clean)
        if match:
            return match.group(1)
        # Match ``` at start and end
        lines = clean.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
            return "\n".join(lines[1:-1])
    return clean


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> str:
        """Send prompt to LLM and return generated string."""
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider supporting modern gemini-2.5-flash / gemini-1.5 models."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model

    def generate(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            raise ValueError(
                "Gemini API Key is not set. Please set the GEMINI_API_KEY environment variable "
                "or pass it in the settings/UI."
            )

        # Attempt using google-genai library if installed
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=settings.temperature,
                ),
            )
            if response.text:
                return clean_code_fence(response.text)
        except ImportError:
            pass

        # Fallback to direct REST API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": settings.temperature},
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return clean_code_fence(text)
            raise RuntimeError(f"No response candidates returned by Gemini: {data}")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI compatible provider (OpenAI, Groq, DeepSeek, OpenRouter)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.model = model or settings.openai_model

    def generate(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            raise ValueError(
                "OpenAI API Key is not set. Please set the OPENAI_API_KEY environment variable."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": settings.temperature,
        }

        url = f"{self.base_url}/chat/completions"
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                text = choices[0].get("message", {}).get("content", "")
                return clean_code_fence(text)
            raise RuntimeError(f"No response choices returned by OpenAI: {data}")


class OllamaProvider(BaseLLMProvider):
    """Local LLM provider using Ollama (free, runs locally, no API key)."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    def generate(self, prompt: str, system_prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": settings.temperature},
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code != 200:
                    raise RuntimeError(f"Ollama error ({resp.status_code}): {resp.text}")
                data = resp.json()
                return clean_code_fence(data.get("response", ""))
        except httpx.ConnectError:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. Make sure Ollama is running (`ollama serve`)."
            )


class HeuristicProvider(BaseLLMProvider):
    """
    Deterministic rule-based repair engine.
    Used for local testing or when no external LLM API key is configured.
    """

    def generate(self, prompt: str, system_prompt: str) -> str:
        # Extract the original code section from prompt
        match = re.search(r"ORIGINAL CODE:\r?\n([\s\S]+?)\r?\n\r?\nPlease output", prompt)
        if not match:
            # Fallback if structure varies
            return prompt

        code = match.group(1)
        fixed_lines = []
        lines = code.splitlines()

        # Heuristic rules for common Python syntax errors
        keywords_needing_colon = (
            "def ", "class ", "if ", "elif ", "else", "for ", "while ",
            "try", "except", "finally", "with "
        )

        for line in lines:
            stripped = line.strip()
            new_line = line

            # Rule 1: Missing colon in Python header statements
            if any(stripped.startswith(kw) for kw in keywords_needing_colon):
                # If doesn't end with ':' and not a continued expression
                if not stripped.endswith(":") and not stripped.endswith("\\"):
                    # Check bracket balance on this line
                    if stripped.count("(") == stripped.count(")") and stripped.count("[") == stripped.count("]"):
                        new_line = line.rstrip() + ":"

            # Rule 2: Unclosed single/double quote on single line
            # Count quotes (ignoring escaped ones)
            single_quotes = len(re.findall(r"(?<!\\)'", new_line))
            double_quotes = len(re.findall(r'(?<!\\)"', new_line))
            if single_quotes % 2 == 1 and not ('"' in new_line and single_quotes == 1):
                new_line = new_line + "'"
            elif double_quotes % 2 == 1 and not ("'" in new_line and double_quotes == 1):
                new_line = new_line + '"'

            # Rule 3: Missing closing parenthesis on single line call
            open_parens = new_line.count("(") - new_line.count(")")
            if open_parens > 0 and ":" not in new_line:
                new_line = new_line + (")" * open_parens)

            # Rule 4: Trailing commas in JSON lines
            if stripped.endswith(",}") or stripped.endswith(",]"):
                new_line = line.replace(",}", "}").replace(",]", "]")

            fixed_lines.append(new_line)

        result = "\n".join(fixed_lines)
        # Trailing comma before closing brace/bracket in multiline JSON
        result = re.sub(r",\s*(\}|\])", r"\1", result)
        return result


def get_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> BaseLLMProvider:
    """Factory to retrieve the appropriate LLM provider."""
    name = (provider_name or settings.default_provider).lower().strip()

    if name in ("gemini", "google"):
        return GeminiProvider(api_key=api_key, model=model)
    elif name in ("openai", "gpt", "deepseek", "groq", "openrouter"):
        return OpenAIProvider(api_key=api_key, model=model)
    elif name == "ollama":
        return OllamaProvider(model=model)
    elif name in ("heuristic", "rule", "mock", "offline"):
        return HeuristicProvider()
    else:
        # Default fallback
        logger.warning(f"Unknown provider '{name}'. Falling back to heuristic/rule provider.")
        return HeuristicProvider()
