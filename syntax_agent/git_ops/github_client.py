"""GitHub REST API client for creating Pull Requests and inspecting repositories."""

import re
from typing import Dict, Optional, Tuple
import httpx
from syntax_agent.config import settings


class GitHubClient:
    """Client for interacting with GitHub REST API."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        self.base_url = "https://api.github.com"

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SyntaxFixer-AI-Agent",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    @staticmethod
    def parse_owner_and_repo(target: str) -> Optional[Tuple[str, str]]:
        """Extract owner and repo name from url or 'owner/repo' slug."""
        clean = target.strip()
        # Case 1: 'owner/repo'
        slug_match = re.match(r"^([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)$", clean)
        if slug_match:
            repo_name = slug_match.group(2)
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            return slug_match.group(1), repo_name

        # Case 2: URL 'https://github.com/owner/repo'
        url_match = re.search(r"github\.com[/:]([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)", clean)
        if url_match:
            repo_name = url_match.group(2)
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            return url_match.group(1), repo_name

        return None

    def get_repo_info(self, owner: str, repo: str) -> Optional[Dict]:
        """Fetch repository details such as default branch."""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, headers=self._headers())
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass
        return None

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head_branch: str,
        base_branch: str = "main",
        body: str = "",
    ) -> Dict:
        """
        Creates a Pull Request on GitHub.
        Returns response dict containing 'html_url' and 'number'.
        """
        if not self.token:
            raise ValueError(
                "GitHub token is required to create a Pull Request. "
                "Set GITHUB_TOKEN environment variable or pass --github-token."
            )

        # Confirm default branch if possible
        repo_info = self.get_repo_info(owner, repo)
        if repo_info and "default_branch" in repo_info:
            base_branch = repo_info["default_branch"]

        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        payload = {
            "title": title,
            "head": head_branch,
            "base": base_branch,
            "body": body,
            "maintainer_can_modify": True,
        }

        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, headers=self._headers(), json=payload)
            if res.status_code == 201:
                data = res.json()
                return {
                    "success": True,
                    "url": data.get("html_url"),
                    "number": data.get("number"),
                    "message": "Pull request created successfully!",
                }
            elif res.status_code == 422:
                # Often occurs if PR already exists or no commits between branches
                return {
                    "success": False,
                    "url": None,
                    "error": f"GitHub API 422: {res.text}",
                }
            else:
                return {
                    "success": False,
                    "url": None,
                    "error": f"GitHub API error ({res.status_code}): {res.text}",
                }
