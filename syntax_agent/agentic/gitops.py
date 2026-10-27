"""GitOps Agent: Autonomously manages branch strategies, staging, commits, and PR creation."""

from pathlib import Path
from typing import List, Optional
from syntax_agent.agentic.state import AgentRole, AgenticState, FileTask, TaskStatus
from syntax_agent.git_ops.github_client import GitHubClient
from syntax_agent.git_ops.repo_manager import RepoManager


class GitOpsAgent:
    """Agent that coordinates git repository version control and GitHub PR automation."""

    def __init__(self, repo_mgr: RepoManager, github_client: Optional[GitHubClient] = None):
        self.repo_mgr = repo_mgr
        self.github_client = github_client or GitHubClient()

    def execute_gitops_lifecycle(
        self,
        state: AgenticState,
        verified_tasks: List[FileTask],
        create_branch: bool = True,
        commit: bool = True,
        push: bool = False,
        create_pr: bool = False,
    ) -> None:
        """Executes the complete GitOps workflow for verified tasks."""
        if not verified_tasks:
            state.log_message(
                sender=AgentRole.GITOPS,
                recipient=AgentRole.ORCHESTRATOR,
                msg_type="GITOPS_SKIPPED",
                content="No verified tasks to commit. Skipping GitOps phase.",
            )
            return

        work_dir = self.repo_mgr.local_path
        has_git = (work_dir / ".git").exists()

        if not has_git:
            state.log_message(
                sender=AgentRole.GITOPS,
                recipient=AgentRole.ORCHESTRATOR,
                msg_type="GITOPS_INFO",
                content=f"Directory '{work_dir}' is not a git repository. Skipping git commit.",
            )
            return

        state.log_message(
            sender=AgentRole.GITOPS,
            recipient=AgentRole.ORCHESTRATOR,
            msg_type="GITOPS_START",
            content=f"Starting GitOps lifecycle for {len(verified_tasks)} verified file(s).",
        )

        branch_name = None
        if create_branch:
            branch_name = self.repo_mgr.create_and_checkout_branch()
            state.git_branch = branch_name
            state.log_message(
                sender=AgentRole.GITOPS,
                recipient=AgentRole.ORCHESTRATOR,
                msg_type="BRANCH_CREATED",
                content=f"Created and switched to git branch: {branch_name}",
            )

        # Stage verified files
        files_to_stage = [t.file_path for t in verified_tasks]
        self.repo_mgr.stage_files(files_to_stage)

        if commit:
            commit_msg = (
                f"fix(syntax): auto-resolve syntax errors in {len(verified_tasks)} file(s)\n\n"
                "Verified by Agentic AI multi-agent cognitive architecture:\n"
                + "\n".join(f"- {t.file_path} ({t.language.upper()})" for t in verified_tasks)
            )
            committed = self.repo_mgr.commit(commit_msg)
            if committed:
                state.log_message(
                    sender=AgentRole.GITOPS,
                    recipient=AgentRole.ORCHESTRATOR,
                    msg_type="COMMIT_CREATED",
                    content=f"Committed changes with message: {commit_msg.splitlines()[0]}",
                )

        if push and branch_name:
            success, out = self.repo_mgr.push(branch_name)
            if success:
                state.log_message(
                    sender=AgentRole.GITOPS,
                    recipient=AgentRole.ORCHESTRATOR,
                    msg_type="PUSH_SUCCESS",
                    content=f"Pushed branch '{branch_name}' to remote origin.",
                )
            else:
                state.log_message(
                    sender=AgentRole.GITOPS,
                    recipient=AgentRole.ORCHESTRATOR,
                    msg_type="PUSH_WARNING",
                    content=f"Push output: {out}",
                )

        if create_pr and branch_name:
            owner_repo = GitHubClient.parse_owner_and_repo(state.target_repo)
            if owner_repo:
                owner, repo = owner_repo
                pr_title = f"🤖 fix(syntax): auto-repair syntax errors across {len(verified_tasks)} file(s)"
                pr_body = self._build_pr_body(state, verified_tasks)

                pr_res = self.github_client.create_pull_request(
                    owner=owner,
                    repo=repo,
                    title=pr_title,
                    head_branch=branch_name,
                    body=pr_body,
                )

                if pr_res.get("success"):
                    state.pr_url = pr_res.get("url")
                    state.log_message(
                        sender=AgentRole.GITOPS,
                        recipient=AgentRole.ORCHESTRATOR,
                        msg_type="PR_CREATED",
                        content=f"GitHub Pull Request created: {state.pr_url}",
                    )
                else:
                    state.log_message(
                        sender=AgentRole.GITOPS,
                        recipient=AgentRole.ORCHESTRATOR,
                        msg_type="PR_ERROR",
                        content=f"Failed to create PR: {pr_res.get('error')}",
                    )

    def _build_pr_body(self, state: AgenticState, verified_tasks: List[FileTask]) -> str:
        body = [
            "## 🤖 Agentic AI: Autonomous Syntax Repair Report",
            "",
            "This Pull Request was generated autonomously by **SyntaxFixer Agentic AI**.",
            "",
            "### 🎯 Execution Summary",
            f"- **Target Repository:** `{state.target_repo}`",
            f"- **Total Files Repaired:** `{len(verified_tasks)}`",
            "- **Compiler / AST Verification:** `100% Passed ✅`",
            "",
            "### 📋 Repaired Files Matrix",
            "| File | Language | Diagnostic Notes | Critic Verdict |",
            "| :--- | :--- | :--- | :--- |",
        ]

        for t in verified_tasks:
            diag = t.diagnostic_notes[0] if t.diagnostic_notes else "Syntax anomaly corrected"
            body.append(f"| `{t.file_path}` | `{t.language.upper()}` | {diag} | `APPROVED ✅` |")

        body.extend([
            "",
            "### 🧠 Multi-Agent Workflow",
            "1. **Planner Agent**: Decomposed repository dependencies and structured execution phases.",
            "2. **Diagnostician Agent**: Isolated root-cause delimiter and grammar anomalies.",
            "3. **Repairer Agent**: Synthesized surgical patches preserving original business logic.",
            "4. **Critic Agent**: Adversarially audited candidate code with native AST compilers.",
            "5. **GitOps Agent**: Staged, committed, and submitted this Pull Request.",
            "",
            "---",
            "*Autonomously created by SyntaxFixer Agentic AI*",
        ])

        return "\n".join(body)
