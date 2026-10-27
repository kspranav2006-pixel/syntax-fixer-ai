"""FastAPI Web Application backend for SyntaxFixer AI Dashboard."""

import os
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from syntax_agent.config import settings
from syntax_agent.detector.base import SyntaxErrorItem
from syntax_agent.detector.registry import detector_registry
from syntax_agent.agent.repair_agent import SyntaxRepairAgent, RepairResult
from syntax_agent.agent.providers import get_provider
from syntax_agent.git_ops.repo_manager import RepoManager
from syntax_agent.git_ops.github_client import GitHubClient

app = FastAPI(title="SyntaxFixer AI Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Request/Response schemas
class ScanRequest(BaseModel):
    target: str = Field(default=".", description="Local directory path or GitHub repo URL")
    github_token: Optional[str] = None


class FixRequest(BaseModel):
    target: str = Field(default=".")
    file_path: str
    provider: str = Field(default="gemini")
    api_key: Optional[str] = None
    model: Optional[str] = None
    write_back: bool = Field(default=True)
    github_token: Optional[str] = None


class BatchFixRequest(BaseModel):
    target: str = Field(default=".")
    provider: str = Field(default="gemini")
    api_key: Optional[str] = None
    model: Optional[str] = None
    create_branch: bool = True
    commit: bool = True
    github_token: Optional[str] = None


class CreatePRRequest(BaseModel):
    target: str
    branch_name: str
    title: Optional[str] = None
    body: Optional[str] = None
    github_token: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>SyntaxFixer Dashboard: static/index.html not found</h1>")
    return FileResponse(index_file)


@app.get("/api/config")
async def get_system_config():
    return {
        "default_provider": settings.default_provider,
        "gemini_model": settings.gemini_model,
        "openai_model": settings.openai_model,
        "ollama_model": settings.ollama_model,
        "has_gemini_key": bool(settings.gemini_api_key),
        "has_openai_key": bool(settings.openai_api_key),
        "has_github_token": bool(settings.github_token),
        "supported_extensions": settings.supported_extensions,
    }


@app.post("/api/scan")
async def scan_repository(req: ScanRequest):
    try:
        repo_mgr = RepoManager(req.target)
        if repo_mgr.is_remote:
            work_dir = repo_mgr.clone_or_update(github_token=req.github_token)
        else:
            work_dir = repo_mgr.local_path

        results = detector_registry.scan_directory(work_dir)
        total_errors = sum(len(errs) for errs in results.values())

        # Format items cleanly
        formatted = {}
        for rel_path, err_list in results.items():
            formatted[rel_path] = [e.model_dump() for e in err_list]

        return {
            "success": True,
            "target": req.target,
            "resolved_path": str(work_dir),
            "is_remote": repo_mgr.is_remote,
            "files_with_errors": len(results),
            "total_errors": total_errors,
            "errors": formatted,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fix")
async def fix_file(req: FixRequest):
    try:
        repo_mgr = RepoManager(req.target)
        work_dir = repo_mgr.local_path

        abs_file = work_dir / req.file_path if not Path(req.file_path).is_absolute() else Path(req.file_path)
        if not abs_file.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {abs_file}")

        provider = get_provider(provider_name=req.provider, api_key=req.api_key, model=req.model)
        agent = SyntaxRepairAgent(provider=provider)

        result = agent.repair_file(abs_file, write_back=req.write_back)
        return {
            "success": result.success,
            "file_path": req.file_path,
            "language": result.language,
            "iterations_used": result.iterations_used,
            "diff": result.diff,
            "repaired_code": result.repaired_code,
            "reflection_logs": result.reflection_logs,
            "remaining_errors": [e.model_dump() for e in result.remaining_errors],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fix-all")
async def fix_all(req: BatchFixRequest):
    try:
        repo_mgr = RepoManager(req.target)
        work_dir = repo_mgr.local_path

        scan_results = detector_registry.scan_directory(work_dir)
        if not scan_results:
            return {"success": True, "message": "No syntax errors found.", "results": []}

        branch_name = None
        if req.create_branch and (work_dir / ".git").exists():
            branch_name = repo_mgr.create_and_checkout_branch()

        provider = get_provider(provider_name=req.provider, api_key=req.api_key, model=req.model)
        agent = SyntaxRepairAgent(provider=provider)

        repair_summaries = []
        fixed_files = []

        for rel_path in scan_results.keys():
            abs_file = work_dir / rel_path if not Path(rel_path).is_absolute() else Path(rel_path)
            res = agent.repair_file(abs_file, write_back=True)
            if res.success:
                fixed_files.append(rel_path)
            repair_summaries.append({
                "file_path": rel_path,
                "success": res.success,
                "iterations_used": res.iterations_used,
                "diff": res.diff,
                "reflection_logs": res.reflection_logs,
            })

        if req.commit and fixed_files and (work_dir / ".git").exists():
            repo_mgr.stage_files(fixed_files)
            repo_mgr.commit(f"fix(syntax): auto-repair {len(fixed_files)} file(s) via SyntaxFixer AI")

        return {
            "success": True,
            "branch_name": branch_name,
            "total_files": len(scan_results),
            "fixed_files_count": len(fixed_files),
            "results": repair_summaries,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create-pr")
async def create_pr(req: CreatePRRequest):
    try:
        client = GitHubClient(token=req.github_token)
        owner_repo = GitHubClient.parse_owner_and_repo(req.target)
        if not owner_repo:
            raise HTTPException(status_code=400, detail="Invalid GitHub repository target")

        owner, repo = owner_repo
        title = req.title or "🤖 fix(syntax): auto-repaired syntax errors"
        body = req.body or "Auto-repaired syntax errors using SyntaxFixer AI Agent."

        res = client.create_pull_request(
            owner=owner,
            repo=repo,
            title=title,
            head_branch=req.branch_name,
            body=body,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AgenticWorkflowRequest(BaseModel):
    target: str = Field(default=".")
    goal: str = Field(default="Autonomously detect, diagnose, repair, and verify all syntax errors in repository.")
    provider: str = Field(default="gemini")
    api_key: Optional[str] = None
    model: Optional[str] = None
    create_branch: bool = True
    commit: bool = True
    push: bool = False
    create_pr: bool = False
    github_token: Optional[str] = None
    dry_run: bool = False
    max_retries: int = 3


@app.post("/api/agentic-run")
async def run_agentic_system(req: AgenticWorkflowRequest):
    from syntax_agent.agentic import AgenticOrchestrator

    try:
        provider = get_provider(provider_name=req.provider, api_key=req.api_key, model=req.model)
        orchestrator = AgenticOrchestrator(provider=provider, max_reflection_retries=req.max_retries)

        state = orchestrator.run_agentic_workflow(
            target=req.target,
            goal=req.goal,
            create_branch=req.create_branch,
            commit=req.commit,
            push=req.push,
            create_pr=req.create_pr,
            github_token=req.github_token,
            dry_run=req.dry_run,
        )

        return {
            "success": state.is_completed,
            "goal": state.goal,
            "target": state.target_repo,
            "resolved_path": state.resolved_path,
            "plan": [p.model_dump() for p in state.plan],
            "file_tasks": {k: v.model_dump() for k, v in state.file_tasks.items()},
            "messages": [m.model_dump() for m in state.messages],
            "git_branch": state.git_branch,
            "pr_url": state.pr_url,
            "summary": state.overall_summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

