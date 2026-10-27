"""Tests for Git and GitHub operations."""

from pathlib import Path
import pytest
from syntax_agent.git_ops.github_client import GitHubClient
from syntax_agent.git_ops.repo_manager import RepoManager


def test_parse_github_slug():
    parsed = GitHubClient.parse_owner_and_repo("octocat/Spoon-Knife")
    assert parsed == ("octocat", "Spoon-Knife")

    parsed_with_git = GitHubClient.parse_owner_and_repo("octocat/Spoon-Knife.git")
    assert parsed == ("octocat", "Spoon-Knife")


def test_parse_github_url():
    url = "https://github.com/google/guava.git"
    parsed = GitHubClient.parse_owner_and_repo(url)
    assert parsed == ("google", "guava")

    ssh_url = "git@github.com:facebook/react.git"
    parsed_ssh = GitHubClient.parse_owner_and_repo(ssh_url)
    assert parsed_ssh == ("facebook", "react")


def test_repo_manager_local_resolution():
    local_dir = Path(".").resolve()
    mgr = RepoManager(str(local_dir))
    assert mgr.is_remote is False
    assert mgr.local_path == local_dir


def test_repo_manager_remote_detection():
    mgr = RepoManager("https://github.com/torvalds/linux")
    assert mgr.is_remote is True
    assert mgr.local_path.name == "linux"
