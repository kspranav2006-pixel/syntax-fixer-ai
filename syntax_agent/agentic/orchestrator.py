"""Agentic Orchestrator: Master cognitive engine coordinating multi-agent syntax repair."""

import difflib
from pathlib import Path
from typing import Callable, Optional
from syntax_agent.config import settings
from syntax_agent.agent.providers import BaseLLMProvider, get_provider
from syntax_agent.agentic.state import AgentRole, AgenticState, FileTask, TaskStatus
from syntax_agent.agentic.planner import PlannerAgent
from syntax_agent.agentic.diagnostician import DiagnosticianAgent
from syntax_agent.agentic.repairer import RepairerAgent
from syntax_agent.agentic.critic import CriticAgent
from syntax_agent.agentic.gitops import GitOpsAgent
from syntax_agent.detector.registry import detector_registry
from syntax_agent.git_ops.repo_manager import RepoManager
from syntax_agent.git_ops.github_client import GitHubClient


class AgenticOrchestrator:
    """Master Orchestrator driving the autonomous multi-agent cognitive architecture."""

    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        max_reflection_retries: Optional[int] = None,
    ):
        self.provider = provider or get_provider()
        self.max_retries = max_reflection_retries or settings.max_reflection_retries

        # Sub-agents
        self.planner = PlannerAgent()
        self.diagnostician = DiagnosticianAgent()
        self.repairer = RepairerAgent(provider=self.provider)
        self.critic = CriticAgent()

    def run_agentic_workflow(
        self,
        target: str,
        goal: str = "Autonomously detect, diagnose, repair, and verify all syntax errors in repository.",
        create_branch: bool = True,
        commit: bool = True,
        push: bool = False,
        create_pr: bool = False,
        github_token: Optional[str] = None,
        dry_run: bool = False,
        message_callback: Optional[Callable] = None,
    ) -> AgenticState:
        """
        Executes the autonomous multi-agent lifecycle:
        Reconnaissance -> Planning -> Diagnosis -> Guided Repair -> Critic Audit -> GitOps
        """
        repo_mgr = RepoManager(target)
        gh_client = GitHubClient(token=github_token)
        gitops = GitOpsAgent(repo_mgr=repo_mgr, github_client=gh_client)

        state = AgenticState(
            goal=goal,
            target_repo=target,
            is_remote=repo_mgr.is_remote,
        )
        if message_callback:
            state.set_message_listener(message_callback)

        def dispatch_message(sender: AgentRole, recipient: AgentRole, msg_type: str, content: str, meta: Optional[dict] = None):
            return state.log_message(sender, recipient, msg_type, content, meta)

        # Step 1: Target Resolution
        dispatch_message(
            AgentRole.ORCHESTRATOR,
            AgentRole.PLANNER,
            "WORKFLOW_INIT",
            f"Goal: '{goal}'. Initializing target: '{target}'.",
        )

        if repo_mgr.is_remote:
            dispatch_message(
                AgentRole.ORCHESTRATOR,
                AgentRole.GITOPS,
                "REMOTE_CLONE_START",
                f"Cloning remote GitHub repository: {target}",
            )
            work_dir = repo_mgr.clone_or_update(github_token=github_token)
        else:
            work_dir = repo_mgr.local_path

        state.resolved_path = str(work_dir)

        # Step 2: Deterministic Reconnaissance
        dispatch_message(
            AgentRole.ORCHESTRATOR,
            AgentRole.DIAGNOSTICIAN,
            "RECONNAISSANCE_START",
            f"Scanning repository for syntax anomalies in: {work_dir}",
        )
        scan_results = detector_registry.scan_directory(work_dir)

        if not scan_results:
            dispatch_message(
                AgentRole.ORCHESTRATOR,
                AgentRole.ORCHESTRATOR,
                "GOAL_SATISFIED",
                "Zero syntax errors detected across repository. Codebase is clean.",
            )
            state.is_completed = True
            state.overall_summary = "Repository is completely free of syntax errors."
            return state

        # Step 3: Planning Phase
        self.planner.create_plan(state, scan_results)

        # Step 4: Multi-Agent Execution Loop across tasks
        verified_tasks = []
        failed_tasks = []

        for rel_path, task in state.file_tasks.items():
            abs_path = work_dir / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
            code = abs_path.read_text(encoding="utf-8", errors="replace")
            task.original_code = code
            task.status = TaskStatus.IN_PROGRESS

            dispatch_message(
                AgentRole.ORCHESTRATOR,
                AgentRole.DIAGNOSTICIAN,
                "TASK_DISPATCH",
                f"Initiating multi-agent resolution for {rel_path} ({len(task.initial_errors)} error(s)).",
            )

            # 4a: Diagnosis
            self.diagnostician.diagnose(state, task, code)

            # 4b: Iterative Repair & Critic Verification Loop
            critique = None
            is_approved = False
            candidate = code

            for attempt in range(1, self.max_retries + 1):
                task.iterations_used = attempt

                # Guided Repair
                candidate = self.repairer.generate_repair(state, task, code, critique_feedback=critique)

                # Critic Evaluation
                is_approved, critique, err = self.critic.evaluate(state, task, candidate, code)

                if is_approved:
                    task.status = TaskStatus.VERIFIED
                    task.repaired_code = candidate
                    task.diff = self._generate_diff(code, candidate, rel_path)

                    if not dry_run:
                        abs_path.write_text(candidate, encoding="utf-8")

                    verified_tasks.append(task)
                    dispatch_message(
                        AgentRole.ORCHESTRATOR,
                        AgentRole.ORCHESTRATOR,
                        "TASK_VERIFIED",
                        f"File {rel_path} successfully repaired and verified in {attempt} attempt(s).",
                    )
                    break
                else:
                    dispatch_message(
                        AgentRole.ORCHESTRATOR,
                        AgentRole.REPAIRER,
                        "REFLECT_RETRY",
                        f"Attempt {attempt}/{self.max_retries} rejected by Critic. Triggering reflection loop with feedback.",
                    )

            if not is_approved:
                task.status = TaskStatus.FAILED
                task.repaired_code = candidate
                task.diff = self._generate_diff(code, candidate, rel_path)
                failed_tasks.append(task)
                dispatch_message(
                    AgentRole.ORCHESTRATOR,
                    AgentRole.ORCHESTRATOR,
                    "TASK_FAILED",
                    f"File {rel_path} could not be fully verified after {self.max_retries} attempts.",
                )

        # Step 5: GitOps Deployment
        if not dry_run and verified_tasks:
            gitops.execute_gitops_lifecycle(
                state=state,
                verified_tasks=verified_tasks,
                create_branch=create_branch,
                commit=commit,
                push=push,
                create_pr=create_pr,
            )

        # Step 6: Final Synthesis
        state.is_completed = len(failed_tasks) == 0
        state.overall_summary = (
            f"Agentic AI Execution Complete: {len(verified_tasks)}/{len(state.file_tasks)} files successfully verified."
        )

        dispatch_message(
            AgentRole.ORCHESTRATOR,
            AgentRole.ORCHESTRATOR,
            "WORKFLOW_COMPLETE",
            state.overall_summary,
            meta={"verified": len(verified_tasks), "failed": len(failed_tasks)},
        )

        return state

    def _generate_diff(self, original: str, fixed: str, filename: str) -> str:
        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile=f"a/{filename}",
                tofile=f"b/{filename}",
            )
        )
        return "".join(diff_lines)
