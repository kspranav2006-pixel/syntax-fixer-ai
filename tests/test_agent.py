"""Tests for syntax repair agent and reflection loop."""

import pytest
from syntax_agent.agent.providers import clean_code_fence, HeuristicProvider, get_provider
from syntax_agent.agent.repair_agent import SyntaxRepairAgent
from syntax_agent.detector.python_check import PythonSyntaxChecker


def test_clean_code_fence():
    fenced = "```python\ndef test():\n    return 42\n```"
    cleaned = clean_code_fence(fenced)
    assert cleaned == "def test():\n    return 42"

    plain = "def test():\n    return 42"
    assert clean_code_fence(plain) == plain


def test_heuristic_provider_repairs_missing_colon():
    provider = HeuristicProvider()
    code = "def add(x, y)\n    return x + y\n"
    prompt = f"Language: PYTHON\nFile: test.py\n\nORIGINAL CODE:\n{code}\n\nPlease output the complete"
    fixed = provider.generate(prompt=prompt, system_prompt="")
    assert "def add(x, y):" in fixed

    # Check that fixed code parses with AST
    checker = PythonSyntaxChecker()
    errors = checker.check_code(fixed)
    assert len(errors) == 0


def test_repair_agent_with_heuristic():
    provider = HeuristicProvider()
    agent = SyntaxRepairAgent(provider=provider, max_retries=2)

    broken_code = "def calculate_tax(amount)\n    if amount > 100\n        return amount * 0.2\n    return 0\n"
    result = agent.repair_code(broken_code, file_path="tax.py")

    assert result.success is True
    assert result.iterations_used >= 1
    assert "def calculate_tax(amount):" in result.repaired_code
    assert "if amount > 100:" in result.repaired_code
    assert len(result.remaining_errors) == 0
    assert result.diff != ""


def test_repair_agent_already_clean_code():
    provider = HeuristicProvider()
    agent = SyntaxRepairAgent(provider=provider)

    clean_code = "def hello():\n    return 'world'\n"
    result = agent.repair_code(clean_code, file_path="hello.py")

    assert result.success is True
    assert result.iterations_used == 0
    assert result.repaired_code == clean_code
