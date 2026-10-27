"""Registry to coordinate multi-language syntax checkers across files and directories."""

from pathlib import Path
from typing import Dict, List, Optional
from syntax_agent.config import settings
from syntax_agent.detector.base import BaseSyntaxChecker, SyntaxErrorItem
from syntax_agent.detector.python_check import PythonSyntaxChecker
from syntax_agent.detector.js_check import JavaScriptSyntaxChecker
from syntax_agent.detector.data_check import JsonSyntaxChecker, YamlSyntaxChecker


class SyntaxDetectorRegistry:
    """Manages language checkers and orchestrates repository-wide syntax scanning."""

    def __init__(self):
        self.checkers: List[BaseSyntaxChecker] = [
            PythonSyntaxChecker(),
            JavaScriptSyntaxChecker(),
            JsonSyntaxChecker(),
            YamlSyntaxChecker(),
        ]

    def register_checker(self, checker: BaseSyntaxChecker) -> None:
        """Register a custom syntax checker."""
        self.checkers.append(checker)

    def get_checker_for_file(self, file_path: Path) -> Optional[BaseSyntaxChecker]:
        """Find the appropriate checker for a given file."""
        for checker in self.checkers:
            if checker.can_check(file_path):
                return checker
        return None

    def scan_file(self, file_path: Path) -> List[SyntaxErrorItem]:
        """Check a single file for syntax errors."""
        checker = self.get_checker_for_file(file_path)
        if not checker:
            return []
        return checker.check_file(file_path)

    def scan_directory(
        self,
        directory_path: Path,
        ignored_dirs: Optional[List[str]] = None,
        allowed_extensions: Optional[List[str]] = None,
    ) -> Dict[str, List[SyntaxErrorItem]]:
        """
        Recursively scan a directory for syntax errors.
        Returns a dict mapping file_path -> list of SyntaxErrorItem.
        """
        results: Dict[str, List[SyntaxErrorItem]] = {}
        ignored = set(ignored_dirs or settings.ignored_directories)
        extensions = set(allowed_extensions or settings.supported_extensions)

        target_dir = Path(directory_path).resolve()
        if not target_dir.exists():
            return results

        # If user passed a single file directly
        if target_dir.is_file():
            errors = self.scan_file(target_dir)
            if errors:
                results[str(target_dir)] = errors
            return results

        for item in target_dir.rglob("*"):
            # Skip directories and ignored directory paths
            if item.is_dir():
                continue

            # Check if any part of the path is in ignored directories (allow .github)
            parts = item.relative_to(target_dir).parts
            if any(part in ignored or (part.startswith(".") and part not in (".github", ".")) for part in parts[:-1]):
                continue

            if item.suffix.lower() not in extensions:
                continue

            errors = self.scan_file(item)
            if errors:
                rel_path = str(item.relative_to(target_dir))
                results[rel_path] = errors

        return results


# Global default instance
detector_registry = SyntaxDetectorRegistry()
