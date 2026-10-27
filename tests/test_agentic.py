"""Tests for Agentic AI multi-agent architecture and orchestrator."""

from pathlib import Path
import pytest
from syntax_agent.agent.providers import HeuristicProvider
from syntax_agent.agentic.orchestrator import AgenticOrchestrator
from syntax_agent.agentic.state import AgentRole, TaskStatus

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_agentic_workflow_execution():
    provider = HeuristicProvider()
    orchestrator = AgenticOrchestrator(provider=provider, max_reflection_retries=2)

    messages = []
    state = orchestrator.run_agentic_workflow(
        target=str(FIXTURES_DIR),
        goal="Autonomously detect and repair syntax errors in fixtures.",
        dry_run=True,
        message_callback=lambda msg: messages.append(msg),
    )

    # 1. Verify Planner created structured plan
    assert len(state.plan) >= 3
    assert state.plan[0].assigned_role == AgentRole.DIAGNOSTICIAN

    # 2. Verify Diagnostician analyzed tasks
    assert len(state.file_tasks) >= 2
    for task in state.file_tasks.values():
        assert len(task.diagnostic_notes) > 0

    # 3. Verify inter-agent messaging exchange occurred
    assert len(messages) > 5
    senders = {m.sender for m in messages}
    assert AgentRole.ORCHESTRATOR in senders
    assert AgentRole.PLANNER in senders
    assert AgentRole.DIAGNOSTICIAN in senders
    assert AgentRole.REPAIRER in senders
    assert AgentRole.CRITIC in senders

    # 4. Verify Critic verified python calculator
    calc_task = next((t for name, t in state.file_tasks.items() if "broken_calculator.py" in name), None)
    assert calc_task is not None
    assert calc_task.status == TaskStatus.VERIFIED
    assert "APPROVED" in (calc_task.critic_verdict or "")
    assert "def calculate_average(numbers):" in (calc_task.repaired_code or "")
