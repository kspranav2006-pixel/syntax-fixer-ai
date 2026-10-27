"""Syntax detector package."""

from syntax_agent.detector.base import BaseSyntaxChecker, SyntaxErrorItem, extract_surrounding_context
from syntax_agent.detector.python_check import PythonSyntaxChecker
from syntax_agent.detector.js_check import JavaScriptSyntaxChecker
from syntax_agent.detector.data_check import JsonSyntaxChecker, YamlSyntaxChecker
from syntax_agent.detector.registry import SyntaxDetectorRegistry, detector_registry

__all__ = [
    "BaseSyntaxChecker",
    "SyntaxErrorItem",
    "extract_surrounding_context",
    "PythonSyntaxChecker",
    "JavaScriptSyntaxChecker",
    "JsonSyntaxChecker",
    "YamlSyntaxChecker",
    "SyntaxDetectorRegistry",
    "detector_registry",
]
