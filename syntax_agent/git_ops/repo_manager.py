"""Git repository manager for cloning, branching, committing, and generating patches."""

import datetime
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class RepoManager:
    """Manages local git operations and remote repository cloning."""

    def __init__(self, repo_path_or_url: str, working_dir: Optional[Path] = None):
        self.target = repo_path_or_url
        self.working_dir = working_dir or Path.cwd()
        self.is_remote = self._is_remote_url(repo_path_or_url)
        self.local_path: Path = self._resolve_path()

    def _is_remote_url(self, target: str) -> bool:
        """Check if target string is a remote Git/GitHub URL."""
        # If path actually exists locally, it's definitely a local target
        if Path(target).exists():
            return False

        return (
            target.startswith("http://")
            or target.startswith("https://")
            or target.startswith("git@")
            or (re.match(r"^[\w\-]+/[\w\-]+$", target) is not None and not Path(target).exists())
        )

    def _resolve_path(self) -> Path:
        """Resolve target to a local Path or clone destination."""
        if not self.is_remote:
            p = Path(self.target).resolve()
            if not p.exists():
                raise FileNotFoundError(f"Target path '{self.target}' does not exist.")
            return p

        # If it's github owner/repo shorthand e.g. "facebook/react"
        url = self.target
        if re.match(r"^[\w\-]+/[\w\-]+$", target := self.target.strip()):
            url = f"https://github.com/{target}.git"

        # Derive repo name
        repo_name = url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        clones_dir = self.working_dir / ".syntax_agent_clones"
        clones_dir.mkdir(parents=True, exist_ok=True)
        return clones_dir / repo_name

    def clone_or_update(self, github_token: Optional[str] = None, branch: Optional[str] = None) -> Path:
        """Clones a remote repository if not already cloned, or pulls latest changes."""
        if not self.is_remote:
            return self.local_path

        url = self.target
        if re.match(r"^[\w\-]+/[\w\-]+$", target := self.target.strip()):
            url = f"https://github.com/{target}.git"

        # Inject token into URL for authenticated cloning if provided
        clone_url = url
        if github_token and "github.com" in clone_url and "@" not in clone_url:
            clone_url = clone_url.replace("https://", f"https://x-access-token:{github_token}@")

        if self.local_path.exists() and (self.local_path / ".git").exists():
            # Pull latest
            self._run_git(["pull"], cwd=self.local_path)
            return self.local_path

        # Clean clone
        if self.local_path.exists():
            shutil.rmtree(self.local_path, ignore_errors=True)

        cmd = ["clone"]
        if branch:
            cmd.extend(["-b", branch])
        cmd.extend([clone_url, str(self.local_path)])

        res = self._run_git(cmd, cwd=self.local_path.parent)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to clone repository: {res.stderr}")

        return self.local_path

    def get_current_branch(self) -> str:
        """Get the current active branch name."""
        res = self._run_git(["branch", "--show-current"])
        return res.stdout.strip() or "main"

    def create_and_checkout_branch(self, branch_name: Optional[str] = None) -> str:
        """Creates a new branch for the syntax fix commits."""
        if not branch_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"fix/syntax-repairs-{timestamp}"

        res = self._run_git(["checkout", "-b", branch_name])
        if res.returncode != 0:
            # Maybe branch already exists
            self._run_git(["checkout", branch_name])

        return branch_name

    def stage_files(self, file_paths: List[str]) -> None:
        """Stage specific files with git add."""
        if not file_paths:
            return
        cmd = ["add"] + file_paths
        self._run_git(cmd)

    def commit(self, message: str) -> bool:
        """Commit staged changes."""
        res = self._run_git(["commit", "-m", message])
        return res.returncode == 0

    def get_diff(self) -> str:
        """Get git diff of changes."""
        res = self._run_git(["diff"])
        return res.stdout

    def export_patch(self, output_path: Path) -> Path:
        """Export current diff to a patch file."""
        diff = self.get_diff()
        output_path.write_text(diff, encoding="utf-8")
        return output_path

    def push(self, branch_name: str, remote: str = "origin") -> Tuple[bool, str]:
        """Push current branch to remote repository."""
        res = self._run_git(["push", "-u", remote, branch_name])
        return res.returncode == 0, res.stderr or res.stdout

    def _run_git(self, args: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Execute a git command within repository directory."""
        work_dir = cwd or self.local_path
        full_cmd = ["git"] + args
        return subprocess.run(
            full_cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
