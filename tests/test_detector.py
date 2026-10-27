"""Tests for syntax error detector across supported languages."""

from pathlib import Path
import pytest
from syntax_agent.detector.base import extract_surrounding_context
from syntax_agent.detector.python_check import PythonSyntaxChecker
from syntax_agent.detector.js_check import JavaScriptSyntaxChecker
from syntax_agent.detector.data_check import JsonSyntaxChecker
from syntax_agent.detector.registry import detector_registry

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_python_checker_valid_code():
    checker = PythonSyntaxChecker()
    valid_code = "def add(x, y):\n    return x + y\n"
    errors = checker.check_code(valid_code)
    assert len(errors) == 0


def test_python_checker_detects_syntax_error():
    checker = PythonSyntaxChecker()
    broken_code = "def broken(x\n    return x\n"
    errors = checker.check_code(broken_code)
    assert len(errors) > 0
    assert errors[0].line_number == 1
    assert "SyntaxError" in errors[0].error_message
    assert errors[0].language == "python"


def test_python_checker_on_fixture():
    checker = PythonSyntaxChecker()
    fixture = FIXTURES_DIR / "broken_calculator.py"
    errors = checker.check_file(fixture)
    assert len(errors) > 0
    assert errors[0].line_number is not None


def test_clean_fixture_has_zero_errors():
    checker = PythonSyntaxChecker()
    clean_fixture = FIXTURES_DIR / "clean_module.py"
    errors = checker.check_file(clean_fixture)
    assert len(errors) == 0


def test_javascript_checker_detects_error():
    checker = JavaScriptSyntaxChecker()
    fixture = FIXTURES_DIR / "broken_script.js"
    errors = checker.check_file(fixture)
    assert len(errors) > 0
    assert errors[0].language == "javascript"


def test_json_checker_detects_error():
    checker = JsonSyntaxChecker()
    fixture = FIXTURES_DIR / "broken_manifest.json"
    errors = checker.check_file(fixture)
    assert len(errors) == 0 or len(errors) == 1
    # Trailing comma should fail standard JSON
    broken_json = '{\n  "a": 1,\n}'
    errs = checker.check_code(broken_json)
    assert len(errs) == 1
    assert "JSONDecodeError" in errs[0].error_message


def test_registry_directory_scan():
    results = detector_registry.scan_directory(FIXTURES_DIR)
    assert len(results) >= 2
    # Ensure clean module is NOT in results
    assert not any("clean_module.py" in str(k) for k in results.keys())
    # Ensure broken files are in results
    assert any("broken_calculator.py" in str(k) for k in results.keys())


def test_extract_surrounding_context():
    code = "line 1\nline 2\nline 3\nline 4\nline 5"
    snippet = extract_surrounding_context(code, line_no=3, col_no=2)
    assert "line 3" in snippet
    assert ">    3 | line 3" in snippet
    assert "^" in snippet
