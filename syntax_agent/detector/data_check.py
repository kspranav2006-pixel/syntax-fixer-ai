"""JSON and YAML syntax error detector."""

import json
from pathlib import Path
from typing import List, Optional
import yaml
from syntax_agent.detector.base import BaseSyntaxChecker, SyntaxErrorItem, extract_surrounding_context


class JsonSyntaxChecker(BaseSyntaxChecker):
    """Syntax checker for JSON (.json) files."""

    def supported_extensions(self) -> List[str]:
        return [".json"]

    def language_name(self) -> str:
        return "json"

    def check_code(self, code: str, file_path: Optional[str] = None) -> List[SyntaxErrorItem]:
        errors: List[SyntaxErrorItem] = []
        path_str = file_path or "<string>"

        if not code.strip():
            return errors

        try:
            json.loads(code)
        except json.JSONDecodeError as err:
            snippet = extract_surrounding_context(code, err.lineno, err.colno)
            errors.append(
                SyntaxErrorItem(
                    file_path=path_str,
                    language=self.language_name(),
                    line_number=err.lineno,
                    column_number=err.colno,
                    error_message=f"JSONDecodeError: {err.msg}",
                    context_snippet=snippet,
                    raw_traceback=str(err),
                )
            )

        return errors


class YamlSyntaxChecker(BaseSyntaxChecker):
    """Syntax checker for YAML (.yaml, .yml) files."""

    def supported_extensions(self) -> List[str]:
        return [".yaml", ".yml"]

    def language_name(self) -> str:
        return "yaml"

    def check_code(self, code: str, file_path: Optional[str] = None) -> List[SyntaxErrorItem]:
        errors: List[SyntaxErrorItem] = []
        path_str = file_path or "<string>"

        if not code.strip():
            return errors

        try:
            # safe_load_all handles multi-document YAML (e.g. k8s or CI manifests)
            list(yaml.safe_load_all(code))
        except yaml.YAMLError as err:
            line_no = None
            col_no = None
            problem = str(err)

            if hasattr(err, "problem_mark") and err.problem_mark:
                # pyyaml line is 0-indexed, col is 0-indexed
                line_no = err.problem_mark.line + 1
                col_no = err.problem_mark.column + 1

            snippet = extract_surrounding_context(code, line_no, col_no) if line_no else ""
            errors.append(
                SyntaxErrorItem(
                    file_path=path_str,
                    language=self.language_name(),
                    line_number=line_no,
                    column_number=col_no,
                    error_message=f"YAMLError: {problem.splitlines()[0] if problem else 'Invalid YAML'}",
                    context_snippet=snippet,
                    raw_traceback=str(err),
                )
            )

        return errors
