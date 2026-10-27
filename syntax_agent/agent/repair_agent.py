"""Self-healing AI Agent for syntax error repair with compiler-in-the-loop reflection."""

import difflib
import logging
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from syntax_agent.config import settings
from syntax_agent.detector.base import SyntaxErrorItem
from syntax_agent.detector.registry import detector_registry
from syntax_agent.agent.prompts import SYNTAX_FIXER_SYSTEM_PROMPT, build_repair_user_prompt
from syntax_agent.agent.providers import BaseLLMProvider, get_provider

logger = logging.getLogger(__name__)


class RepairAttempt(BaseModel):
    """Details of a single iteration attempt in the reflection loop."""
    iteration: int
    candidate_code: str
    errors_found: List[SyntaxErrorItem] = Field(default_factory=list)
    success: bool = False


class RepairResult(BaseModel):
    """Overall outcome of the syntax repair agent on a file."""
    file_path: str
    language: str
    success: bool
    iterations_used: int
    max_retries: int
    original_code: str
    repaired_code: str
    diff: str
    initial_errors: List[SyntaxErrorItem]
    remaining_errors: List[SyntaxErrorItem] = Field(default_factory=list)
    reflection_logs: List[str] = Field(default_factory=list)


class SyntaxRepairAgent:
    """Agent that repairs syntax errors using an iterative reflection loop with AST verification."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None, max_retries: Optional[int] = None):
        self.provider = provider or get_provider()
        self.max_retries = max_retries or settings.max_reflection_retries

    def repair_code(
        self,
        code: str,
        file_path: str,
        initial_errors: Optional[List[SyntaxErrorItem]] = None,
    ) -> RepairResult:
        """
        Runs the self-correcting agent loop on code string:
        Detect -> Generate Fix -> Validate AST -> Reflect/Retry -> Finalize
        """
        logs: List[str] = []
        path_obj = Path(file_path)
        checker = detector_registry.get_checker_for_file(path_obj)
        language = checker.language_name() if checker else "unknown"

        # Detect initial errors if not provided
        if initial_errors is None:
            if checker:
                initial_errors = checker.check_code(code, file_path=file_path)
            else:
                initial_errors = []

        if not initial_errors:
            logs.append(f"No syntax errors detected in {file_path}. Skipping.")
            return RepairResult(
                file_path=file_path,
                language=language,
                success=True,
                iterations_used=0,
                max_retries=self.max_retries,
                original_code=code,
                repaired_code=code,
                diff="",
                initial_errors=[],
                remaining_errors=[],
                reflection_logs=logs,
            )

        logs.append(
            f"Detected {len(initial_errors)} syntax error(s) in {file_path}. Initiating repair agent..."
        )

        current_code = code
        previous_feedback = ""
        last_errors = initial_errors
        best_candidate = code

        for attempt in range(1, self.max_retries + 1):
            logs.append(f"Iteration {attempt}/{self.max_retries}: Consulting LLM provider...")

            error_summary = "\n".join(e.format_summary() for e in last_errors)
            error_snippets = "\n\n".join(
                f"--- Error at Line {e.line_number or '?'} ---\n{e.context_snippet}"
                for e in last_errors
                if e.context_snippet
            )

            prompt = build_repair_user_prompt(
                language=language,
                file_path=file_path,
                code=current_code,
                error_summary=error_summary,
                error_snippets=error_snippets,
                previous_attempt_feedback=previous_feedback,
            )

            try:
                candidate = self.provider.generate(
                    prompt=prompt,
                    system_prompt=SYNTAX_FIXER_SYSTEM_PROMPT,
                )
            except Exception as e:
                logs.append(f"Iteration {attempt} failed: Provider exception: {e}")
                break

            if not candidate.strip():
                logs.append(f"Iteration {attempt}: Provider returned empty response.")
                continue

            # Deterministic AST validation check
            if checker:
                new_errors = checker.check_code(candidate, file_path=file_path)
            else:
                new_errors = []

            if not new_errors:
                logs.append(
                    f"Success! Iteration {attempt} passed compiler verification with zero syntax errors."
                )
                diff = self._generate_diff(code, candidate, file_path)
                return RepairResult(
                    file_path=file_path,
                    language=language,
                    success=True,
                    iterations_used=attempt,
                    max_retries=self.max_retries,
                    original_code=code,
                    repaired_code=candidate,
                    diff=diff,
                    initial_errors=initial_errors,
                    remaining_errors=[],
                    reflection_logs=logs,
                )

            # Still has syntax errors -> Prepare reflection feedback for next iteration
            logs.append(
                f"Iteration {attempt} candidate still contained {len(new_errors)} error(s): "
                f"{new_errors[0].error_message}"
            )
            feedback_lines = []
            for err in new_errors:
                feedback_lines.append(
                    f"- Line {err.line_number or '?'}: {err.error_message}\n{err.context_snippet}"
                )
            previous_feedback = "\n".join(feedback_lines)
            last_errors = new_errors
            best_candidate = candidate

        # If loop finished without full resolution
        logs.append(
            f"Failed to completely resolve all syntax errors after {self.max_retries} attempts."
        )
        diff = self._generate_diff(code, best_candidate, file_path)
        return RepairResult(
            file_path=file_path,
            language=language,
            success=False,
            iterations_used=self.max_retries,
            max_retries=self.max_retries,
            original_code=code,
            repaired_code=best_candidate,
            diff=diff,
            initial_errors=initial_errors,
            remaining_errors=last_errors,
            reflection_logs=logs,
        )

    def repair_file(self, file_path: Path, write_back: bool = False) -> RepairResult:
        """Reads file, repairs errors, and optionally writes clean code back to disk."""
        code = file_path.read_text(encoding="utf-8", errors="replace")
        result = self.repair_code(code, str(file_path))
        if write_back and result.success:
            file_path.write_text(result.repaired_code, encoding="utf-8")
        return result

    def _generate_diff(self, original: str, fixed: str, filename: str) -> str:
        """Generate unified diff string."""
        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile=f"a/{filename}",
                tofile=f"b/{filename}",
            )
        )
        return "".join(diff_lines)
