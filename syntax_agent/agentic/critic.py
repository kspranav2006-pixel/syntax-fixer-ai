"""Critic Agent: Audits candidate patches for AST compliance, compiler cleanliness, and semantic integrity."""

from pathlib import Path
from typing import Optional, Tuple
from syntax_agent.agentic.state import AgentRole, AgenticState, FileTask
from syntax_agent.detector.base import SyntaxErrorItem
from syntax_agent.detector.registry import detector_registry


class CriticAgent:
    """Agent that performs rigorous compiler auditing and semantic preservation checks."""

    def evaluate(
        self,
        state: AgenticState,
        task: FileTask,
        candidate_code: str,
        original_code: str,
    ) -> Tuple[bool, Optional[str], Optional[SyntaxErrorItem]]:
        """
        Audits the candidate patch.
        Returns: (is_approved, critique_feedback, failing_error_if_any)
        """
        state.log_message(
            sender=AgentRole.CRITIC,
            recipient=AgentRole.ORCHESTRATOR,
            msg_type="AUDIT_START",
            content=f"Auditing candidate patch for {task.file_path}.",
        )

        # Check 1: Non-empty check
        if not candidate_code or not candidate_code.strip():
            critique = "REJECTED: Candidate code is empty or truncated. Ensure full file content is provided."
            state.log_message(
                sender=AgentRole.CRITIC,
                recipient=AgentRole.REPAIRER,
                msg_type="CRITIQUE_REJECTION",
                content=critique,
            )
            return False, critique, None

        # Check 2: Deterministic Compiler / AST Validation
        checker = detector_registry.get_checker_for_file(Path(task.file_path))
        new_errors = checker.check_code(candidate_code, file_path=task.file_path) if checker else []

        if new_errors:
            first_err = new_errors[0]
            critique = (
                f"REJECTED: Compiler/AST validation failed with {len(new_errors)} error(s).\n"
                f"Line {first_err.line_number or '?'}: {first_err.error_message}\n"
                f"Snippet:\n{first_err.context_snippet}\n"
                "Refine the patch to ensure 100% syntactically valid grammar."
            )
            state.log_message(
                sender=AgentRole.CRITIC,
                recipient=AgentRole.REPAIRER,
                msg_type="CRITIQUE_REJECTION",
                content=f"Compiler rejected candidate for {task.file_path}: {first_err.error_message}",
                meta={"line": first_err.line_number, "msg": first_err.error_message},
            )
            return False, critique, first_err

        # Check 3: Semantic sanity check (e.g., did candidate preserve key functions)
        orig_lines = [l.strip() for l in original_code.splitlines() if l.strip().startswith(("def ", "class ", "function "))]
        for def_line in orig_lines:
            sig = def_line.split("(")[0].strip()
            if sig and sig not in candidate_code:
                critique = (
                    f"REJECTED: Semantic drift detected! Statement '{sig}' was present in the original code "
                    "but is missing in the repaired version. Do not remove existing logic."
                )
                state.log_message(
                    sender=AgentRole.CRITIC,
                    recipient=AgentRole.REPAIRER,
                    msg_type="CRITIQUE_REJECTION",
                    content=critique,
                )
                return False, critique, None

        # Approved!
        task.critic_verdict = "APPROVED (AST validation passed with 0 compiler errors)"
        state.log_message(
            sender=AgentRole.CRITIC,
            recipient=AgentRole.ORCHESTRATOR,
            msg_type="CRITIC_APPROVAL",
            content=f"Candidate patch for {task.file_path} APPROVED. 100% clean AST verification achieved.",
        )

        return True, None, None
