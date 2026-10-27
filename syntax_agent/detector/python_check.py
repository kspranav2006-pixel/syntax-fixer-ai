"""Python syntax error detector using AST parser and compile validation."""

import ast
from pathlib import Path
from typing import List, Optional
from syntax_agent.detector.base import BaseSyntaxChecker, SyntaxErrorItem, extract_surrounding_context


class PythonSyntaxChecker(BaseSyntaxChecker):
    """Syntax checker for Python (.py, .pyw) files."""

    def supported_extensions(self) -> List[str]:
        return [".py", ".pyw"]

    def language_name(self) -> str:
        return "python"

    def check_code(self, code: str, file_path: Optional[str] = None) -> List[SyntaxErrorItem]:
        errors: List[SyntaxErrorItem] = []
        path_str = file_path or "<string>"

        # Empty files or pure comments/docstrings have valid syntax
        if not code.strip():
            return errors

        try:
            # 1. AST Parse validation
            ast.parse(code, filename=path_str)
            # 2. Built-in compile check for bytecode issues
            compile(code, filename=path_str, mode="exec")
        except (SyntaxError, IndentationError) as err:
            line_no = err.lineno
            col_no = err.offset
            snippet = extract_surrounding_context(code, line_no, col_no)
            msg = f"{err.__class__.__name__}: {err.msg}"
            
            errors.append(
                SyntaxErrorItem(
                    file_path=path_str,
                    language=self.language_name(),
                    line_number=line_no,
                    column_number=col_no,
                    error_message=msg,
                    context_snippet=snippet,
                    raw_traceback=f"File '{path_str}', line {line_no}\n  {err.text.strip() if err.text else ''}\n{msg}",
                )
            )
        except Exception as e:
            errors.append(
                SyntaxErrorItem(
                    file_path=path_str,
                    language=self.language_name(),
                    line_number=None,
                    column_number=None,
                    error_message=f"Parser exception: {e}",
                    context_snippet="",
                    raw_traceback=str(e),
                )
            )

        return errors
