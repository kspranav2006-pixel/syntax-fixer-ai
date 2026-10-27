"""Command Line Interface for SyntaxFixer AI Agent."""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from syntax_agent.config import settings
from syntax_agent.detector.registry import detector_registry
from syntax_agent.agent.repair_agent import SyntaxRepairAgent
from syntax_agent.agent.providers import get_provider
from syntax_agent.git_ops.repo_manager import RepoManager
from syntax_agent.git_ops.github_client import GitHubClient

# Reconfigure stdout/stderr for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name="syntax-agent",
    help="AI Agent for detecting and repairing syntax errors in GitHub repositories.",
    add_completion=False,
)
console = Console(highlight=False)


@app.command()
def scan(
    target: str = typer.Argument(".", help="Path to local directory/file or GitHub repository URL"),
    github_token: Optional[str] = typer.Option(None, "--github-token", "-t", help="GitHub Personal Access Token"),
):
    """Scan a repository or directory for syntax errors across all supported languages."""
    console.print(Panel.fit("[bold cyan]SyntaxFixer AI[/bold cyan] - Scanning for syntax errors...", border_style="cyan"))

    repo_mgr = RepoManager(target)
    if repo_mgr.is_remote:
        console.print("[bold green]Cloning remote repository...[/bold green]")
        scan_dir = repo_mgr.clone_or_update(github_token=github_token)
        console.print(f"[dim]Cloned to: {scan_dir}[/dim]")
    else:
        scan_dir = repo_mgr.local_path

    console.print(f"[yellow]Analyzing repository syntax in:[/] [cyan]{scan_dir}[/]")
    results = detector_registry.scan_directory(scan_dir)

    if not results:
        console.print("[bold green]✨ Zero syntax errors found! The repository is clean.[/bold green]")
        return

    table = Table(title="[bold red]Detected Syntax Errors[/bold red]", show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan")
    table.add_column("Lang", style="yellow")
    table.add_column("Line:Col", style="green")
    table.add_column("Error Message", style="red")

    total_errors = 0
    for file_path, errors in results.items():
        for err in errors:
            total_errors += 1
            loc = f"{err.line_number or '?'}:{err.column_number or '?'}"
            table.add_row(file_path, err.language.upper(), loc, err.error_message)

    console.print(table)
    console.print(f"\n[bold yellow]Total syntax errors: {total_errors} across {len(results)} file(s).[/bold yellow]")
    console.print("Run [bold cyan]syntax-agent fix <target>[/bold cyan] to automatically repair them!")


@app.command()
def fix(
    target: str = typer.Argument(".", help="Path to local directory/file or GitHub repository URL"),
    provider: str = typer.Option("gemini", "--provider", "-p", help="LLM Provider: 'gemini', 'openai', 'ollama', 'heuristic'"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API Key for the chosen provider"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Custom model name"),
    create_branch: bool = typer.Option(True, "--branch/--no-branch", help="Create a dedicated git branch for fixes"),
    commit: bool = typer.Option(True, "--commit/--no-commit", help="Commit fixes to git branch"),
    push: bool = typer.Option(False, "--push", help="Push branch to remote origin"),
    create_pr: bool = typer.Option(False, "--pr", help="Automatically open a GitHub Pull Request"),
    github_token: Optional[str] = typer.Option(None, "--github-token", "-t", help="GitHub Personal Access Token"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview fixes and diffs without modifying files"),
    export_patch: Optional[Path] = typer.Option(None, "--patch", help="Save unified diff as a .patch file"),
    max_retries: int = typer.Option(3, "--max-retries", "-r", help="Maximum compiler-reflection iterations per file"),
):
    """Automatically scan and repair syntax errors using self-healing reflection."""
    console.print(Panel.fit("[bold cyan]SyntaxFixer AI Agent[/bold cyan] - Self-Healing Repair Mode", border_style="cyan"))

    repo_mgr = RepoManager(target)
    if repo_mgr.is_remote:
        console.print("[bold green]Cloning remote repository...[/bold green]")
        work_dir = repo_mgr.clone_or_update(github_token=github_token)
        console.print(f"[dim]Cloned to: {work_dir}[/dim]")
    else:
        work_dir = repo_mgr.local_path

    # Step 1: Scan
    console.print(f"[bold]Scanning for syntax errors in:[/] [cyan]{work_dir}[/]")
    scan_results = detector_registry.scan_directory(work_dir)

    if not scan_results:
        console.print("[bold green]✨ No syntax errors found! Nothing to fix.[/bold green]")
        return

    console.print(f"[yellow]Found syntax errors in {len(scan_results)} file(s). Starting repair agent...[/yellow]\n")

    # Step 2: Initialize provider and agent
    try:
        llm_provider = get_provider(provider_name=provider, api_key=api_key, model=model)
    except Exception as e:
        console.print(f"[bold red]Failed to initialize provider '{provider}': {e}[/bold red]")
        sys.exit(1)

    agent = SyntaxRepairAgent(provider=llm_provider, max_retries=max_retries)

    branch_name = None
    if not dry_run and create_branch and (work_dir / ".git").exists():
        branch_name = repo_mgr.create_and_checkout_branch()
        console.print(f"[green]Created and checked out git branch:[/] [bold]{branch_name}[/bold]\n")

    repaired_files = []
    failed_files = []
    all_diffs = []

    for rel_path, errors in scan_results.items():
        file_path = work_dir / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
        console.print(f"🔧 [bold cyan]Processing:[/] {rel_path} ({len(errors)} error(s))")

        result = agent.repair_file(file_path, write_back=(not dry_run))

        for log_line in result.reflection_logs:
            console.print(f"   [dim]{log_line}[/dim]")

        if result.success:
            console.print(f"   ✅ [bold green]Verified Fix![/bold green] (in {result.iterations_used} iteration(s))")
            repaired_files.append(str(file_path))
            if result.diff:
                all_diffs.append(result.diff)
                syntax = Syntax(result.diff, "diff", theme="monokai", line_numbers=False)
                console.print(Panel(syntax, title=f"Diff: {rel_path}", border_style="green"))
        else:
            console.print(f"   ❌ [bold red]Repair incomplete.[/bold red] {len(result.remaining_errors)} error(s) remain.")
            failed_files.append(str(file_path))

        console.print("")

    # Summary
    console.print(Panel.fit(
        f"[bold]Repair Summary:[/bold]\n"
        f"✅ Successfully Repaired: [bold green]{len(repaired_files)}[/bold green] file(s)\n"
        f"❌ Remaining Issues: [bold red]{len(failed_files)}[/bold red] file(s)",
        border_style="cyan"
    ))

    # Export patch if requested
    if export_patch and all_diffs:
        export_patch.write_text("\n\n".join(all_diffs), encoding="utf-8")
        console.print(f"[bold green]Patch saved to:[/] {export_patch.resolve()}")

    # Git commit & PR
    if not dry_run and repaired_files and (work_dir / ".git").exists():
        if commit:
            rel_repaired = [str(Path(f).relative_to(work_dir)) for f in repaired_files]
            repo_mgr.stage_files(rel_repaired)
            commit_msg = f"fix(syntax): automatically resolve syntax errors in {len(repaired_files)} file(s)"
            repo_mgr.commit(commit_msg)
            console.print(f"[bold green]Committed changes to branch:[/] {branch_name}")

        if push and branch_name:
            console.print("[bold green]Pushing branch to remote origin...[/bold green]")
            success, out = repo_mgr.push(branch_name)
            if success:
                console.print(f"[bold green]Pushed branch {branch_name} to remote.[/bold green]")
            else:
                console.print(f"[yellow]Push output: {out}[/yellow]")

        if create_pr and branch_name:
            client = GitHubClient(token=github_token)
            owner_repo = GitHubClient.parse_owner_and_repo(target)
            if owner_repo:
                owner, repo = owner_repo
                console.print("[bold green]Creating GitHub Pull Request...[/bold green]")
                pr_body = (
                    "### 🤖 Automated Syntax Repair\n\n"
                    f"SyntaxFixer AI Agent detected and automatically repaired syntax errors in `{len(repaired_files)}` file(s).\n\n"
                    "#### Repaired Files:\n"
                )
                for f in repaired_files:
                    pr_body += f"- `{Path(f).name}` (AST validation passed ✅)\n"
                pr_body += "\n*Powered by SyntaxFixer AI Agent*"

                pr_res = client.create_pull_request(
                    owner=owner,
                    repo=repo,
                    title=f"🤖 fix(syntax): auto-repair syntax errors in {len(repaired_files)} file(s)",
                    head_branch=branch_name,
                    body=pr_body,
                )
                if pr_res.get("success"):
                    console.print(f"[bold green]🎉 Pull Request Created:[/] {pr_res.get('url')}")
                else:
                    console.print(f"[bold red]Failed to create PR:[/] {pr_res.get('error')}")
            else:
                console.print("[yellow]Could not determine GitHub repository owner/repo for PR creation.[/yellow]")

from syntax_agent.agentic import AgenticOrchestrator, AgentRole, TaskStatus


@app.command()
def agentic(
    target: str = typer.Argument(".", help="Path to local directory/file or GitHub repository URL"),
    goal: str = typer.Option("Autonomously detect, diagnose, repair, and verify all syntax errors in repository.", "--goal", "-g", help="High-level autonomous objective for the agentic system"),
    provider: str = typer.Option("gemini", "--provider", "-p", help="LLM Provider: 'gemini', 'openai', 'ollama', 'heuristic'"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API Key for the chosen provider"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Custom model name"),
    create_branch: bool = typer.Option(True, "--branch/--no-branch", help="Create a dedicated git branch for fixes"),
    commit: bool = typer.Option(True, "--commit/--no-commit", help="Commit fixes to git branch"),
    push: bool = typer.Option(False, "--push", help="Push branch to remote origin"),
    create_pr: bool = typer.Option(False, "--pr", help="Automatically open a GitHub Pull Request"),
    github_token: Optional[str] = typer.Option(None, "--github-token", "-t", help="GitHub Personal Access Token"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview fixes and diffs without modifying files"),
    max_retries: int = typer.Option(3, "--max-retries", "-r", help="Maximum compiler-reflection iterations per file"),
):
    """Execute the Agentic AI autonomous multi-agent cognitive architecture."""
    console.print(Panel.fit(
        "[bold magenta]SyntaxFixer Agentic AI[/bold magenta] - [bold cyan]Multi-Agent Cognitive System[/bold cyan]\n"
        f"[dim]Goal: {goal}[/dim]",
        border_style="magenta",
    ))

    try:
        llm_provider = get_provider(provider_name=provider, api_key=api_key, model=model)
    except Exception as e:
        console.print(f"[bold red]Failed to initialize provider '{provider}': {e}[/bold red]")
        sys.exit(1)

    orchestrator = AgenticOrchestrator(
        provider=llm_provider,
        max_reflection_retries=max_retries,
    )

    role_colors = {
        AgentRole.ORCHESTRATOR: "bold cyan",
        AgentRole.PLANNER: "bold magenta",
        AgentRole.DIAGNOSTICIAN: "bold blue",
        AgentRole.REPAIRER: "bold yellow",
        AgentRole.CRITIC: "bold green",
        AgentRole.GITOPS: "bold white",
    }

    def on_agent_message(msg):
        sender_col = role_colors.get(msg.sender, "white")
        recip_col = role_colors.get(msg.recipient, "white")
        console.print(
            f"[{sender_col}][{msg.sender.value}][/] -> [{recip_col}][{msg.recipient.value}][/] "
            f"([dim]{msg.message_type}[/dim]): {msg.content}"
        )

    state = orchestrator.run_agentic_workflow(
        target=target,
        goal=goal,
        create_branch=create_branch,
        commit=commit,
        push=push,
        create_pr=create_pr,
        github_token=github_token,
        dry_run=dry_run,
        message_callback=on_agent_message,
    )

    # Render Phased Plan Table
    if state.plan:
        plan_table = Table(title="[bold magenta]Agentic Execution Plan[/bold magenta]", show_header=True)
        plan_table.add_column("Step", style="dim", width=6)
        plan_table.add_column("Phase Title", style="cyan")
        plan_table.add_column("Assigned Agent", style="yellow")
        plan_table.add_column("Status", style="green")

        for s in state.plan:
            status_style = "green" if s.status == TaskStatus.VERIFIED else ("yellow" if s.status == TaskStatus.IN_PROGRESS else "dim")
            plan_table.add_row(f"#{s.step_id}", s.title, s.assigned_role.value, f"[{status_style}]{s.status.value.upper()}[/{status_style}]")
        console.print("\n")
        console.print(plan_table)

    # Render File Tasks Matrix
    if state.file_tasks:
        task_table = Table(title="[bold green]File Tasks & Critic Audits[/bold green]", show_header=True)
        task_table.add_column("File", style="cyan")
        task_table.add_column("Lang", style="yellow")
        task_table.add_column("Attempts", style="dim")
        task_table.add_column("Status", style="bold")
        task_table.add_column("Critic Verdict", style="green")

        for f_path, t in state.file_tasks.items():
            status_col = "green" if t.status == TaskStatus.VERIFIED else "red"
            verdict = t.critic_verdict or "Pending audit"
            task_table.add_row(
                f_path,
                t.language.upper(),
                str(t.iterations_used),
                f"[{status_col}]{t.status.value.upper()}[/{status_col}]",
                verdict,
            )
        console.print("\n")
        console.print(task_table)

    # Diffs
    for t in state.file_tasks.values():
        if t.diff:
            syntax = Syntax(t.diff, "diff", theme="monokai", line_numbers=False)
            console.print(Panel(syntax, title=f"Verified Patch: {t.file_path}", border_style="green"))

    # Summary
    console.print(Panel.fit(
        f"[bold]Agentic Execution Summary:[/bold]\n"
        f"{state.overall_summary}\n"
        + (f"Git Branch: [bold green]{state.git_branch}[/bold green]\n" if state.git_branch else "")
        + (f"Pull Request: [bold cyan]{state.pr_url}[/bold cyan]" if state.pr_url else ""),
        border_style="magenta",
    ))


@app.command()
def ui(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address for the Web Dashboard"),
    port: int = typer.Option(8000, "--port", "-p", help="Port for the Web Dashboard"),
):
    """Launch the interactive Web Dashboard."""
    import uvicorn
    console.print(Panel.fit(
        f"[bold cyan]Launching SyntaxFixer AI Dashboard...[/bold cyan]\n"
        f"Server running at: [bold green]http://{host}:{port}[/bold green]",
        border_style="cyan"
    ))
    uvicorn.run("syntax_agent.web.app:app", host=host, port=port, reload=False)


@app.command()
def version():
    """Show version and environment information."""
    console.print("[bold cyan]SyntaxFixer AI Agent[/bold cyan] v1.0.0")
    console.print(f"Python: {sys.version.split()[0]}")
    console.print(f"Default Provider: {settings.default_provider}")
    console.print(f"Supported Extensions: {', '.join(settings.supported_extensions)}")


if __name__ == "__main__":
    app()
