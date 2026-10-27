"""Planner Agent: Analyzes repository structure and formulates a multi-phase execution plan."""

from pathlib import Path
from typing import Dict, List
from syntax_agent.agentic.state import AgentRole, AgenticState, FileTask, PlanStep, TaskStatus
from syntax_agent.detector.base import SyntaxErrorItem


class PlannerAgent:
    """Agent responsible for goal decomposition, dependency ordering, and execution planning."""

    def create_plan(
        self,
        state: AgenticState,
        scan_results: Dict[str, List[SyntaxErrorItem]],
    ) -> List[PlanStep]:
        """Decomposes the syntax repair objective into an actionable multi-phase plan."""
        plan: List[PlanStep] = []
        step_id = 1

        state.log_message(
            sender=AgentRole.PLANNER,
            recipient=AgentRole.ORCHESTRATOR,
            msg_type="PLAN_INITIALIZATION",
            content=f"Analyzing {len(scan_results)} files with syntax errors to build optimal repair plan.",
        )

        # Step 1: Reconnaissance
        plan.append(
            PlanStep(
                step_id=step_id,
                title="Repository Reconnaissance & Error Categorization",
                description="Scan and map all syntax anomalies across Python, JS, JSON, and YAML files.",
                assigned_role=AgentRole.DIAGNOSTICIAN,
                status=TaskStatus.VERIFIED,
                result_summary=f"Identified {len(scan_results)} broken files across codebase.",
            )
        )
        step_id += 1

        # Classify and prioritize files
        config_files = []
        core_files = []

        for rel_path, errors in scan_results.items():
            ext = Path(rel_path).suffix.lower()
            lang = errors[0].language if errors else "unknown"

            # Manifests/Configs take priority as they configure build/tooling environments
            priority = 1 if ext in (".json", ".yaml", ".yml") else 2

            task = FileTask(
                file_path=rel_path,
                language=lang,
                priority=priority,
                initial_errors=errors,
            )
            state.file_tasks[rel_path] = task

            if priority == 1:
                config_files.append(rel_path)
            else:
                core_files.append(rel_path)

        # Step 2: Configuration repair phase (if any)
        if config_files:
            plan.append(
                PlanStep(
                    step_id=step_id,
                    title="Phase 1: Configuration & Manifest Syntax Repairs",
                    description=f"Repair configuration files ({', '.join(Path(f).name for f in config_files)}) to stabilize build manifests.",
                    assigned_role=AgentRole.REPAIRER,
                )
            )
            step_id += 1

        # Step 3: Source code repair phase
        if core_files:
            plan.append(
                PlanStep(
                    step_id=step_id,
                    title="Phase 2: Source Code Surgical Repair",
                    description=f"Perform compiler-directed repairs on {len(core_files)} source files ({', '.join(Path(f).name for f in core_files[:3])}...).",
                    assigned_role=AgentRole.REPAIRER,
                )
            )
            step_id += 1

        # Step 4: Multi-Agent Critic & Semantic Audit
        plan.append(
            PlanStep(
                step_id=step_id,
                title="Phase 3: Adversarial Critic & AST Verification",
                description="Subject every repaired file to compiler AST validation and semantic drift check.",
                assigned_role=AgentRole.CRITIC,
            )
        )
        step_id += 1

        # Step 5: GitOps & Pull Request Delivery
        plan.append(
            PlanStep(
                step_id=step_id,
                title="Phase 4: GitOps Staging, Branching & PR Creation",
                description="Stage verified changes, commit to dedicated branch, and create GitHub Pull Request.",
                assigned_role=AgentRole.GITOPS,
            )
        )

        state.plan = plan

        state.log_message(
            sender=AgentRole.PLANNER,
            recipient=AgentRole.ORCHESTRATOR,
            msg_type="PLAN_COMPLETE",
            content=f"Plan formulated with {len(plan)} structured phases.",
            meta={"phases_count": len(plan), "tasks_count": len(state.file_tasks)},
        )

        return plan
