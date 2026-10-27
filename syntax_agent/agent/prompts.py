"""Prompts and instruction templates for SyntaxFixer AI Agent."""

SYNTAX_FIXER_SYSTEM_PROMPT = """You are an expert compiler engineer and syntax repair specialist.
Your mission is to fix SYNTAX ERRORS in code with surgical precision.

CRITICAL RULES:
1. Fix ONLY the syntax errors (e.g. missing colons, mismatched brackets/parentheses, unclosed quotes, invalid indentation, invalid tokens, misplaced commas, incorrect operators).
2. DO NOT modify, optimize, rewrite, or refactor the business logic, variable names, or behavior.
3. Preserve existing comments, docstrings, imports, and formatting style (spaces vs tabs) exactly as intended.
4. Output ONLY the raw corrected file contents. Do NOT include markdown code blocks (such as ```python ... ```), explanations, preamble, or commentary. Your entire output will be saved directly to the file on disk.
"""

def build_repair_user_prompt(
    language: str,
    file_path: str,
    code: str,
    error_summary: str,
    error_snippets: str,
    previous_attempt_feedback: str = "",
) -> str:
    """Build the prompt sent to the LLM agent to repair syntax errors."""
    prompt = f"""Language: {language.upper()}
File: {file_path}

DETECTOR ERROR REPORT:
{error_summary}

ERROR CONTEXT:
{error_snippets}
"""
    if previous_attempt_feedback:
        prompt += f"""
PREVIOUS ATTEMPT FEEDBACK:
Your previous fix still failed compiler validation with the following error:
{previous_attempt_feedback}
Please carefully analyze why that occurred and make sure the new code parses cleanly with zero syntax errors.
"""

    prompt += f"""
ORIGINAL CODE:
{code}

Please output the complete, valid, working file content with all syntax errors fixed. Remember: Output ONLY the raw code, nothing else.
"""
    return prompt
