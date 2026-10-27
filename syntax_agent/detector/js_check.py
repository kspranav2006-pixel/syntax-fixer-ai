"""JavaScript syntax error detector using Node.js syntax checker."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from syntax_agent.detector.base import BaseSyntaxChecker, SyntaxErrorItem, extract_surrounding_context


class JavaScriptSyntaxChecker(BaseSyntaxChecker):
    """Syntax checker for JavaScript (.js, .mjs, .cjs) files."""

    def __init__(self):
        self.node_available = shutil.which("node") is not None

    def supported_extensions(self) -> List[str]:
        return [".js", ".mjs", ".cjs"]

    def language_name(self) -> str:
        return "javascript"

    def _parse_node_stderr(self, stderr: str, code: str, file_path: str) -> Optional[SyntaxErrorItem]:
        """Parse node stderr output into a structured SyntaxErrorItem."""
        # Example stderr:
        # /path/to/file.js:1
        # function test( { return 123; }
        #                         ^^^
        # SyntaxError: Unexpected number
        match = re.search(r":(\d+)(?::(\d+))?", stderr)
        line_no = None
        col_no = None
        if match:
            try:
                line_no = int(match.group(1))
                if match.group(2):
                    col_no = int(match.group(2))
            except (ValueError, TypeError):
                pass

        error_msg = "JavaScript Syntax Error"
        for line in stderr.splitlines():
            line_strip = line.strip()
            if line_strip.startswith("SyntaxError:") or "Error:" in line_strip:
                error_msg = line_strip
                break

        snippet = extract_surrounding_context(code, line_no, col_no) if line_no else ""

        return SyntaxErrorItem(
            file_path=file_path,
            language=self.language_name(),
            line_number=line_no,
            column_number=col_no,
            error_message=error_msg,
            context_snippet=snippet,
            raw_traceback=stderr.strip(),
        )

    def check_code(self, code: str, file_path: Optional[str] = None) -> List[SyntaxErrorItem]:
        errors: List[SyntaxErrorItem] = []
        path_str = file_path or "<string>"

        if not code.strip():
            return errors

        if not self.node_available:
            # Fallback basic balance check if node is missing
            return self._fallback_delimiter_check(code, path_str)

        # Detect if file uses ES module syntax (import/export)
        is_module = bool(re.search(r"^\s*(import\s+|export\s+)", code, re.MULTILINE))
        suffix = ".mjs" if is_module else (Path(file_path).suffix if file_path else ".js")
        if not suffix:
            suffix = ".mjs" if is_module else ".js"

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as f:
                f.write(code)
                temp_file = f.name

            # Run node --check
            cmd = ["node", "--check", temp_file]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            # If failed because of module vs CJS mismatch, retry with alternative extension
            if res.returncode != 0:
                if "Cannot use import statement outside a module" in res.stderr and suffix != ".mjs":
                    # Retry as .mjs
                    Path(temp_file).unlink(missing_ok=True)
                    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as f:
                        f.write(code)
                        temp_file = f.name
                    res = subprocess.run(["node", "--check", temp_file], capture_output=True, text=True, timeout=10)

            if res.returncode != 0:
                item = self._parse_node_stderr(res.stderr, code, path_str)
                if item:
                    errors.append(item)

        except subprocess.TimeoutExpired:
            errors.append(
                SyntaxErrorItem(
                    file_path=path_str,
                    language=self.language_name(),
                    line_number=None,
                    column_number=None,
                    error_message="Node syntax check timed out",
                    context_snippet="",
                    raw_traceback=None,
                )
            )
        except Exception as e:
            errors.append(
                SyntaxErrorItem(
                    file_path=path_str,
                    language=self.language_name(),
                    line_number=None,
                    column_number=None,
                    error_message=f"Checker execution error: {e}",
                    context_snippet="",
                    raw_traceback=str(e),
                )
            )
        finally:
            if temp_file:
                try:
                    Path(temp_file).unlink(missing_ok=True)
                except Exception:
                    pass

        return errors

    def _fallback_delimiter_check(self, code: str, file_path: str) -> List[SyntaxErrorItem]:
        """Simple delimiter stack check when node is unavailable."""
        delimiters = {"(": ")", "{": "}", "[": "]"}
        reverse = {")": "(", "}": "{", "]": "["}
        stack = []
        lines = code.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            for col_idx, char in enumerate(line, start=1):
                if char in delimiters:
                    stack.append((char, line_idx, col_idx))
                elif char in reverse:
                    if not stack:
                        return [
                            SyntaxErrorItem(
                                file_path=file_path,
                                language=self.language_name(),
                                line_number=line_idx,
                                column_number=col_idx,
                                error_message=f"Unmatched closing delimiter '{char}'",
                                context_snippet=extract_surrounding_context(code, line_idx, col_idx),
                            )
                        ]
                    last, l_idx, c_idx = stack.pop()
                    if delimiters[last] != char:
                        return [
                            SyntaxErrorItem(
                                file_path=file_path,
                                language=self.language_name(),
                                line_number=line_idx,
                                column_number=col_idx,
                                error_message=f"Mismatched delimiter: expected '{delimiters[last]}' but found '{char}'",
                                context_snippet=extract_surrounding_context(code, line_idx, col_idx),
                            )
                        ]

        if stack:
            last, l_idx, c_idx = stack[-1]
            return [
                SyntaxErrorItem(
                    file_path=file_path,
                    language=self.language_name(),
                    line_number=l_idx,
                    column_number=c_idx,
                    error_message=f"Unclosed delimiter '{last}'",
                    context_snippet=extract_surrounding_context(code, l_idx, c_idx),
                )
            ]

        return []
