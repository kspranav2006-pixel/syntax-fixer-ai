"""Diagnostician Agent: Performs root-cause analysis on compiler errors and AST anomalies."""

import re
from typing import List
from syntax_agent.agentic.state import AgentRole, AgenticState, FileTask
from syntax_agent.detector.base import SyntaxErrorItem


class DiagnosticianAgent:
    """Agent that performs semantic and structural root-cause diagnosis of syntax failures."""

    def diagnose(self, state: AgenticState, task: FileTask, code: str) -> List[str]:
        """Analyzes syntax errors and produces actionable diagnostic hypotheses."""
        diagnostics: List[str] = []
        errors = task.initial_errors

        state.log_message(
            sender=AgentRole.DIAGNOSTICIAN,
            recipient=AgentRole.ORCHESTRATOR,
            msg_type="DIAGNOSIS_START",
            content=f"Diagnosing root causes for {task.file_path} ({len(errors)} error(s)).",
        )

        for err in errors:
            msg = err.error_message.lower()
            line_no = err.line_number or 0

            # Diagnosis 1: Unclosed delimiters (often reported on next line or EOF)
            if "unexpected eof" in msg or "unclosed" in msg or "was never closed" in msg:
                diagnostics.append(
                    f"Root Cause Hypothesis: Unterminated delimiter (parenthesis/quote/brace) prior to line {line_no}. "
                    "Repair Strategy: Inspect open delimiters and close them at the logical boundary without dropping code."
                )

            # Diagnosis 2: Missing colon in Python statements
            elif "expected ':'" in msg or "':'" in msg:
                diagnostics.append(
                    f"Root Cause Hypothesis: Missing colon on line {line_no} statement header. "
                    "Repair Strategy: Append ':' to compound statement definition while keeping parameters intact."
                )

            # Diagnosis 3: Trailing comma in JSON
            elif "trailing comma" in msg or ("jsondecodeerror" in msg and "," in err.context_snippet):
                diagnostics.append(
                    f"Root Cause Hypothesis: Invalid trailing comma in JSON collection near line {line_no}. "
                    "Repair Strategy: Strip trailing comma before closing brace/bracket."
                )

            # Diagnosis 4: JavaScript token error
            elif "unexpected token" in msg:
                diagnostics.append(
                    f"Root Cause Hypothesis: Unexpected token '{err.context_snippet.strip()}' at line {line_no}. "
                    "Repair Strategy: Verify preceding operator/delimiter and restore valid expression syntax."
                )

            # Diagnosis 5: Indentation
            elif "indentation" in msg or "unexpected indent" in msg:
                diagnostics.append(
                    f"Root Cause Hypothesis: Indentation divergence at line {line_no}. "
                    "Repair Strategy: Align indent with enclosing block convention (4 spaces)."
                )

            else:
                diagnostics.append(
                    f"Root Cause Hypothesis: Syntax breakdown at line {line_no}: '{err.error_message}'. "
                    "Repair Strategy: Parse surrounding tokens and apply canonical language syntax."
                )

        task.diagnostic_notes = diagnostics

        state.log_message(
            sender=AgentRole.DIAGNOSTICIAN,
            recipient=AgentRole.REPAIRER,
            msg_type="DIAGNOSTIC_BRIEF",
            content=f"Diagnosis ready for {task.file_path}: {len(diagnostics)} tactical insights formulated.",
            meta={"diagnostics": diagnostics},
        )

        return diagnostics
