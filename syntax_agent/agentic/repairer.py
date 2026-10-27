"""Repairer Agent: Synthesizes surgical code patches based on diagnostic briefs."""

from typing import Optional
from syntax_agent.agentic.state import AgentRole, AgenticState, FileTask
from syntax_agent.agent.providers import BaseLLMProvider


class RepairerAgent:
    """Agent that synthesizes candidate syntax repairs under diagnostic guidance."""

    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def generate_repair(
        self,
        state: AgenticState,
        task: FileTask,
        code: str,
        critique_feedback: Optional[str] = None,
    ) -> str:
        """Generates a candidate fix guided by the Diagnostician and Critic."""
        state.log_message(
            sender=AgentRole.REPAIRER,
            recipient=AgentRole.ORCHESTRATOR,
            msg_type="GENERATING_CANDIDATE",
            content=f"Synthesizing surgical repair for {task.file_path} (Attempt {task.iterations_used + 1}).",
        )

        diagnostic_summary = "\n".join(f"- {d}" for d in task.diagnostic_notes)

        prompt = f"""Language: {task.language.upper()}
File: {task.file_path}

DIAGNOSTICIAN ROOT CAUSE BRIEF:
{diagnostic_summary}
"""
        if critique_feedback:
            prompt += f"""
ADVERSARIAL CRITIC FEEDBACK:
{critique_feedback}
"""

        prompt += f"""
ORIGINAL CODE:
{code}

Please output the complete, valid, working file content with all syntax errors fixed. Remember: Output ONLY the raw code, nothing else.
"""

        system_prompt = (
            "You are a specialized code repair agent operating within a multi-agent system. "
            "Follow the Diagnostician's tactical brief closely. Fix only syntax errors. "
            "Do not modify logic or remove comments. Output ONLY the raw code without markdown fences."
        )

        candidate = self.provider.generate(prompt=prompt, system_prompt=system_prompt)

        state.log_message(
            sender=AgentRole.REPAIRER,
            recipient=AgentRole.CRITIC,
            msg_type="CANDIDATE_SUBMISSION",
            content=f"Candidate patch synthesized for {task.file_path}. Submitting to Critic for audit.",
        )

        return candidate
