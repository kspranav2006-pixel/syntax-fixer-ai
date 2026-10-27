"""Base classes and data models for syntax error detection."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


class SyntaxErrorItem(BaseModel):
    """Represents a detected syntax error in a file."""
    file_path: str = Field(description="Relative or absolute path of the file")
    language: str = Field(description="Programming or markup language")
    line_number: Optional[int] = Field(default=None, description="1-indexed line number of error")
    column_number: Optional[int] = Field(default=None, description="1-indexed column number of error")
    error_message: str = Field(description="Compiler/parser error message")
    context_snippet: str = Field(default="", description="Surrounding code lines with pointer")
    raw_traceback: Optional[str] = Field(default=None, description="Underlying parser trace if available")

    def format_summary(self) -> str:
        """User-friendly summary of the syntax error."""
        location = f":{self.line_number}" if self.line_number else ""
        if self.column_number:
            location += f":{self.column_number}"
        return f"[{self.language.upper()}] {self.file_path}{location} -> {self.error_message}"


class BaseSyntaxChecker(ABC):
    """Abstract base class for all language-specific syntax checkers."""

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """List of file extensions supported by this checker (e.g. ['.py'])."""
        pass

    @abstractmethod
    def language_name(self) -> str:
        """Human-readable language name (e.g. 'python', 'javascript')."""
        pass

    def can_check(self, file_path: Path) -> bool:
        """Return True if this checker handles the given file."""
        return file_path.suffix.lower() in self.supported_extensions()

    @abstractmethod
    def check_code(self, code: str, file_path: Optional[str] = None) -> List[SyntaxErrorItem]:
        """Check raw code string for syntax errors."""
        pass

    def check_file(self, file_path: Path) -> List[SyntaxErrorItem]:
        """Read file and check for syntax errors."""
        if not file_path.is_file():
            return []
        try:
            code = file_path.read_text(encoding="utf-8", errors="replace")
            return self.check_code(code, file_path=str(file_path))
        except Exception as e:
            return [
                SyntaxErrorItem(
                    file_path=str(file_path),
                    language=self.language_name(),
                    line_number=None,
                    column_number=None,
                    error_message=f"Could not read file: {e}",
                    context_snippet="",
                    raw_traceback=str(e),
                )
            ]


def extract_surrounding_context(code: str, line_no: Optional[int], col_no: Optional[int] = None, context_lines: int = 3) -> str:
    """Helper to extract snippet around the error line with line numbers and caret."""
    if not line_no:
        return ""
    lines = code.splitlines()
    if not lines:
        return ""

    start = max(0, line_no - 1 - context_lines)
    end = min(len(lines), line_no + context_lines)

    output = []
    for idx in range(start, end):
        current_line_no = idx + 1
        prefix = ">" if current_line_no == line_no else " "
        output.append(f"{prefix} {current_line_no:4d} | {lines[idx]}")
        if current_line_no == line_no and col_no is not None and col_no > 0:
            pointer_indent = " " * (8 + col_no - 1)
            output.append(f"{pointer_indent}^")

    return "\n".join(output)
