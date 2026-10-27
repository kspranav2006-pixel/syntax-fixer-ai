"""Agentic state, memory, and inter-agent communication data models."""

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from syntax_agent.detector.base import SyntaxErrorItem


class AgentRole(str, Enum):
    ORCHESTRATOR = "Orchestrator"
    PLANNER = "Planner"
    DIAGNOSTICIAN = "Diagnostician"
    REPAIRER = "Repairer"
    CRITIC = "Critic"
    GITOPS = "GitOps"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentMessage(BaseModel):
    """Inter-agent communication message."""
    sender: AgentRole
    recipient: AgentRole
    message_type: str = Field(description="e.g. 'TASK_DELEGATION', 'DIAGNOSIS', 'CANDIDATE_PATCH', 'CRITIQUE', 'STATUS_UPDATE'")
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3])


class PlanStep(BaseModel):
    """Discrete step created during the agentic planning phase."""
    step_id: int
    title: str
    description: str
    assigned_role: AgentRole
    status: TaskStatus = TaskStatus.PENDING
    result_summary: Optional[str] = None


class FileTask(BaseModel):
    """File-level work item managed across the multi-agent system."""
    file_path: str
    language: str
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    original_code: str = ""
    repaired_code: Optional[str] = None
    diff: str = ""
    initial_errors: List[SyntaxErrorItem] = Field(default_factory=list)
    diagnostic_notes: List[str] = Field(default_factory=list)
    critic_verdict: Optional[str] = None
    iterations_used: int = 0


class AgenticState(BaseModel):
    """Shared blackboard memory and operational state for the Agentic AI system."""
    goal: str
    target_repo: str
    resolved_path: str = ""
    is_remote: bool = False
    plan: List[PlanStep] = Field(default_factory=list)
    file_tasks: Dict[str, FileTask] = Field(default_factory=dict)
    messages: List[AgentMessage] = Field(default_factory=list)
    git_branch: Optional[str] = None
    pr_url: Optional[str] = None
    is_completed: bool = False
    overall_summary: str = ""
    _message_listener: Optional[Any] = None

    def set_message_listener(self, listener: Any):
        self._message_listener = listener

    def log_message(self, sender: AgentRole, recipient: AgentRole, msg_type: str, content: str, meta: Optional[Dict] = None):
        msg = AgentMessage(
            sender=sender,
            recipient=recipient,
            message_type=msg_type,
            content=content,
            metadata=meta or {},
        )
        self.messages.append(msg)
        if self._message_listener:
            try:
                self._message_listener(msg)
            except Exception:
                pass
        return msg
