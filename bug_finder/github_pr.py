#!/usr/bin/env python3
"""
GitHub PR Integration Module

This module provides functions to interact with GitHub Pull Requests via the `gh` CLI.
It handles fetching PR details, diffs, reviews, comments, and checking out PR branches.
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


# Custom exceptions for PR operations
class GHCLIError(Exception):
    """Base exception for gh CLI errors."""
    pass


class GHCLINotInstalled(GHCLIError):
    """gh CLI is not installed."""
    pass


class GHCLINotAuthenticated(GHCLIError):
    """gh CLI is not authenticated."""
    pass


class PRNotFound(GHCLIError):
    """PR number doesn't exist."""
    pass


class PRAccessDenied(GHCLIError):
    """Permission denied accessing PR."""
    pass


class PRCheckoutFailed(GHCLIError):
    """Failed to checkout PR branch."""
    pass


@dataclass
class GHCLIStatus:
    """Status of gh CLI installation and authentication."""
    installed: bool
    authenticated: bool
    error: Optional[str] = None


def check_gh_cli() -> GHCLIStatus:
    """
    Check if gh CLI is installed and authenticated.
    
    Returns:
        GHCLIStatus with installation and authentication status
    """
    # Check if gh is installed
    try:
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return GHCLIStatus(installed=False, authenticated=False, error="gh CLI not found")
    except FileNotFoundError:
        return GHCLIStatus(installed=False, authenticated=False, error="gh CLI not installed")
    except subprocess.TimeoutExpired:
        return GHCLIStatus(installed=False, authenticated=False, error="gh CLI timed out")
    
    # Check authentication status
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return GHCLIStatus(
                installed=True, 
                authenticated=False, 
                error="gh CLI not authenticated. Run 'gh auth login' first."
            )
    except subprocess.TimeoutExpired:
        return GHCLIStatus(installed=True, authenticated=False, error="Auth check timed out")
    
    return GHCLIStatus(installed=True, authenticated=True)


def infer_current_repo(workspace: Optional[str] = None) -> Optional[str]:
    """
    Infer repository from git remote (owner/repo format).
    
    Args:
        workspace: Optional path to git workspace
        
    Returns:
        Repository in owner/repo format, or None if not in a git repo
    """
    try:
        cwd = workspace if workspace else None
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback: parse git remote
    try:
        cwd = workspace if workspace else None
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Handle SSH format: git@github.com:owner/repo.git
            if url.startswith("git@github.com:"):
                repo = url.replace("git@github.com:", "").replace(".git", "")
                return repo
            # Handle HTTPS format: https://github.com/owner/repo.git
            if "github.com/" in url:
                parts = url.split("github.com/")[1]
                repo = parts.replace(".git", "")
                return repo
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return None


def _run_gh_command(args: list, repo: Optional[str] = None, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """
    Run a gh CLI command with optional repo specification.
    
    Args:
        args: Command arguments (without 'gh' prefix)
        repo: Optional repository in owner/repo format
        cwd: Optional working directory
        
    Returns:
        CompletedProcess result
        
    Raises:
        PRNotFound: If PR doesn't exist
        PRAccessDenied: If access is denied
        GHCLIError: For other gh CLI errors
    """
    cmd = ["gh"] + args
    if repo:
        cmd.extend(["--repo", repo])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd
        )
        
        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "could not find pull request" in stderr or "404" in stderr:
                raise PRNotFound(f"PR not found: {result.stderr}")
            if "403" in stderr or "permission" in stderr or "forbidden" in stderr:
                raise PRAccessDenied(f"Access denied: {result.stderr}")
            raise GHCLIError(f"gh command failed: {result.stderr}")
        
        return result
    except subprocess.TimeoutExpired as e:
        raise GHCLIError(f"Command timed out: {' '.join(cmd)}") from e


def fetch_pr_details(pr_number: int, repo: Optional[str] = None) -> dict:
    """
    Fetch PR metadata.
    
    Args:
        pr_number: Pull request number
        repo: Repository in owner/repo format (optional)
        
    Returns:
        Dictionary with PR details including:
        - number, title, body, state, author
        - baseRefName, headRefName, headRepository
        - files (list of changed files with additions/deletions)
    """
    fields = [
        "number", "title", "body", "state", "author",
        "baseRefName", "headRefName", "headRepository",
        "files", "additions", "deletions", "changedFiles",
        "createdAt", "updatedAt", "url"
    ]
    
    result = _run_gh_command([
        "pr", "view", str(pr_number),
        "--json", ",".join(fields)
    ], repo=repo)
    
    return json.loads(result.stdout)


def fetch_pr_diff(pr_number: int, repo: Optional[str] = None) -> str:
    """
    Fetch PR diff as raw text.
    
    Args:
        pr_number: Pull request number
        repo: Repository in owner/repo format (optional)
        
    Returns:
        Raw diff text
    """
    result = _run_gh_command(["pr", "diff", str(pr_number)], repo=repo)
    return result.stdout


def parse_pr_diff_for_files(diff: str) -> List[str]:
    """
    Extract changed file paths from diff text.
    
    Args:
        diff: Raw diff text
        
    Returns:
        List of file paths that were changed
    """
    files = []
    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            # Format: diff --git a/path/to/file b/path/to/file
            parts = line.split(" b/")
            if len(parts) >= 2:
                file_path = parts[-1]
                if file_path and file_path not in files:
                    files.append(file_path)
    return files


def _parse_paginated_json(output: str) -> List[dict]:
    """
    Parse concatenated JSON arrays from gh api --paginate output.
    
    gh api --paginate outputs concatenated JSON arrays like: [{...}][{...}]
    This function handles that by finding all JSON arrays and combining them.
    
    Args:
        output: Raw output from gh api --paginate
        
    Returns:
        Combined list of all items from all pages
    """
    if not output.strip():
        return []
    
    # Try simple parse first (single page case)
    try:
        result = json.loads(output)
        if isinstance(result, list):
            return result
        return [result]
    except json.JSONDecodeError:
        pass
    
    # Handle concatenated JSON arrays: [{...}][{...}]
    items = []
    
    # Use a bracket-balancing approach to find each JSON array
    # Track string context to ignore brackets inside strings
    depth = 0
    start = None
    parse_errors = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(output):
        # Handle escape sequences inside strings
        if escape_next:
            escape_next = False
            continue
        if char == '\\' and in_string:
            escape_next = True
            continue
        
        # Track string boundaries
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        # Only count brackets outside of strings
        if not in_string:
            if char == '[':
                if depth == 0:
                    start = i
                depth += 1
            elif char == ']':
                depth -= 1
                # Only process if depth is back to 0 (valid close)
                if depth == 0 and start is not None:
                    try:
                        arr = json.loads(output[start:i+1])
                        if isinstance(arr, list):
                            items.extend(arr)
                    except json.JSONDecodeError:
                        parse_errors += 1
                    start = None
                elif depth < 0:
                    # Reset on invalid state
                    depth = 0
                    start = None
    
    if parse_errors > 0:
        import sys
        print(f"Warning: Failed to parse {parse_errors} JSON array(s) from paginated output", file=sys.stderr)
    
    return items


def fetch_pr_reviews(pr_number: int, repo: Optional[str] = None) -> List[dict]:
    """
    Fetch all review comments (review body + inline comments).
    
    Args:
        pr_number: Pull request number
        repo: Repository in owner/repo format (optional)
        
    Returns:
        List of review dictionaries with author, state, body, and comments
    """
    # Get review summaries
    result = _run_gh_command([
        "pr", "view", str(pr_number),
        "--json", "reviews"
    ], repo=repo)
    
    data = json.loads(result.stdout)
    reviews = data.get("reviews", [])
    
    # Get inline review comments via API (with pagination limit)
    # Limit to 500 comments to prevent hanging on very large PRs
    MAX_INLINE_COMMENTS = 500
    try:
        repo_name = repo or infer_current_repo()
        if repo_name:
            # Use per_page parameter and limit total pages
            api_result = _run_gh_command([
                "api", f"/repos/{repo_name}/pulls/{pr_number}/comments",
                "--paginate",
                "-f", "per_page=100"  # Fetch 100 per page
            ])
            # Handle concatenated JSON from paginated output
            inline_comments = _parse_paginated_json(api_result.stdout)
            
            # Limit the number of inline comments to prevent performance issues
            if len(inline_comments) > MAX_INLINE_COMMENTS:
                inline_comments = inline_comments[:MAX_INLINE_COMMENTS]
            
            # Add inline comments as separate entries
            for comment in inline_comments:
                comment_data = {
                    "author": comment.get("user", {}).get("login", "Unknown"),
                    "body": comment.get("body", ""),
                    "path": comment.get("path", ""),
                    "line": comment.get("line") or comment.get("original_line"),
                    "diff_hunk": comment.get("diff_hunk", ""),
                    "created_at": comment.get("created_at", ""),
                }
                
                # Try to find a matching review to group this comment under
                # Since we don't have easy IDs, we'll just keep them as separate entries
                # for now but with a consistent format.
                reviews.append({
                    "author": {"login": comment_data["author"]},
                    "state": "INLINE_COMMENT",
                    "body": comment_data["body"],
                    "path": comment_data["path"],
                    "line": comment_data["line"],
                    "created_at": comment_data["created_at"]
                })
    except GHCLIError:
        # If API call fails, just return the basic reviews
        pass
    
    return reviews


def fetch_pr_comments(pr_number: int, repo: Optional[str] = None) -> List[dict]:
    """
    Fetch general PR comments (issue comments, not inline code comments).
    
    Args:
        pr_number: Pull request number
        repo: Repository in owner/repo format (optional)
        
    Returns:
        List of comment dictionaries with author and body
    """
    result = _run_gh_command([
        "pr", "view", str(pr_number),
        "--json", "comments"
    ], repo=repo)
    
    data = json.loads(result.stdout)
    return data.get("comments", [])


def checkout_pr_branch(
    pr_number: int, 
    repo: Optional[str] = None, 
    workspace: Optional[str] = None
) -> dict:
    """
    Checkout PR's head branch locally, handling cross-repo (fork) PRs.
    
    Args:
        pr_number: Pull request number
        repo: Repository in owner/repo format (optional)
        workspace: Working directory for checkout
        
    Returns:
        Dictionary with success status, branch name, and any error
    """
    try:
        # gh pr checkout handles cross-repo PRs automatically
        cmd = ["pr", "checkout", str(pr_number)]
        if repo:
            cmd.extend(["--repo", repo])
        
        result = subprocess.run(
            ["gh"] + cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=workspace
        )
        
        if result.returncode != 0:
            # Check for common issues
            stderr = result.stderr.lower()
            if "already exists" in stderr or "already checked out" in stderr:
                # Already on the branch, that's fine
                return {
                    "success": True,
                    "branch": f"pr-{pr_number}",
                    "error": None,
                    "message": "Branch already checked out"
                }
            if "uncommitted changes" in stderr or "overwritten" in stderr:
                raise PRCheckoutFailed(
                    "Uncommitted changes would be overwritten. "
                    "Please commit or stash your changes first."
                )
            raise PRCheckoutFailed(f"Checkout failed: {result.stderr}")
        
        # Try to get the current branch name
        try:
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=workspace
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else f"pr-{pr_number}"
        except Exception:
            branch = f"pr-{pr_number}"
        
        return {
            "success": True,
            "branch": branch,
            "error": None,
            "message": "Successfully checked out PR branch"
        }
        
    except subprocess.TimeoutExpired:
        raise PRCheckoutFailed("Checkout timed out")
    except PRCheckoutFailed:
        raise
    except Exception as e:
        raise PRCheckoutFailed(f"Unexpected error during checkout: {e}") from e


def get_current_branch(workspace: Optional[str] = None) -> Optional[str]:
    """
    Get the current git branch name.
    
    Args:
        workspace: Working directory
        
    Returns:
        Current branch name or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=workspace
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def restore_branch(branch: str, workspace: Optional[str] = None) -> bool:
    """
    Restore to a specific git branch.
    
    Args:
        branch: Branch name to checkout
        workspace: Working directory
        
    Returns:
        True if successful, False otherwise
    """
    if not branch:
        return False
    try:
        result = subprocess.run(
            ["git", "checkout", branch],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=workspace
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def format_reviewer_comments_for_ai(reviews: list, comments: list) -> str:
    """
    Format existing reviewer feedback in a structured way for AI consumption.
    
    Args:
        reviews: List of review dictionaries
        comments: List of comment dictionaries
        
    Returns:
        Formatted string of reviewer feedback
    """
    parts = []
    
    if reviews:
        parts.append("=== EXISTING REVIEWER FEEDBACK ===\n")
        for i, review in enumerate(reviews, 1):
            author = review.get("author", {})
            if isinstance(author, dict):
                author_name = author.get("login", "Unknown")
            else:
                author_name = str(author)
            
            state = review.get("state", "COMMENTED")
            body = review.get("body", "").strip()
            
            if body:
                parts.append(f"### Review #{i} by {author_name} ({state})\n{body}\n")
            
            # Include inline comments if present
            path = review.get("path")
            line = review.get("line")
            if path and line:
                parts.append(f"  📍 File: {path}, Line: {line}\n")
    
    if comments:
        parts.append("\n=== PR DISCUSSION COMMENTS ===\n")
        for i, comment in enumerate(comments, 1):
            author = comment.get("author", {})
            if isinstance(author, dict):
                author_name = author.get("login", "Unknown")
            else:
                author_name = str(author)
            
            body = comment.get("body", "").strip()
            if body:
                parts.append(f"### Comment #{i} by {author_name}\n{body}\n")
    
    if not parts:
        return "No existing reviewer feedback found."
    
    return "\n".join(parts)


def format_pr_context_for_agents(
    pr_details: dict,
    pr_diff: str,
    pr_reviews: List[dict],
    pr_comments: List[dict],
) -> str:
    """
    Compile all PR data into a formatted string for AI agents.
    
    Args:
        pr_details: PR metadata dictionary
        pr_diff: Raw diff text
        pr_reviews: List of reviews
        pr_comments: List of comments
        
    Returns:
        Formatted context string for AI agents
    """
    parts = []
    
    # PR Header
    parts.append(f"# Pull Request #{pr_details.get('number', 'Unknown')}")
    parts.append(f"**Title:** {pr_details.get('title', 'Unknown')}")
    parts.append(f"**State:** {pr_details.get('state', 'Unknown')}")
    
    author = pr_details.get("author", {})
    if isinstance(author, dict):
        author_name = author.get("login", "Unknown")
    else:
        author_name = str(author)
    parts.append(f"**Author:** {author_name}")
    
    parts.append(f"**Base Branch:** {pr_details.get('baseRefName', 'Unknown')}")
    parts.append(f"**Head Branch:** {pr_details.get('headRefName', 'Unknown')}")
    parts.append(f"**URL:** {pr_details.get('url', 'N/A')}")
    parts.append("")
    
    # PR Description
    parts.append("## Description")
    body = pr_details.get("body", "").strip()
    parts.append(body if body else "_No description provided_")
    parts.append("")
    
    # Changed Files Summary
    parts.append("## Changed Files")
    files = pr_details.get("files", [])
    additions = pr_details.get("additions", 0)
    deletions = pr_details.get("deletions", 0)
    parts.append(f"Total: {len(files)} files, +{additions} -{deletions}")
    parts.append("")
    
    for f in files[:30]:  # Limit to first 30 files
        path = f.get("path", "Unknown")
        adds = f.get("additions", 0)
        dels = f.get("deletions", 0)
        parts.append(f"- {path} (+{adds} -{dels})")
    
    if len(files) > 30:
        parts.append(f"... and {len(files) - 30} more files")
    parts.append("")
    
    # Reviewer Feedback
    reviewer_feedback = format_reviewer_comments_for_ai(pr_reviews, pr_comments)
    parts.append(reviewer_feedback)
    parts.append("")
    
    # Diff (truncated if too large)
    parts.append("## PR Diff")
    if len(pr_diff) > 50000:
        parts.append(pr_diff[:50000])
        parts.append("\n... [diff truncated due to size] ...")
    else:
        parts.append(pr_diff)
    
    return "\n".join(parts)


def get_pr_changed_file_paths(pr_number: int, repo: Optional[str] = None, workspace: Optional[str] = None) -> List[str]:
    """
    Get absolute paths to PR changed files in the local workspace.
    
    Args:
        pr_number: Pull request number
        repo: Repository in owner/repo format (optional)
        workspace: Local workspace path
        
    Returns:
        List of absolute file paths
    """
    pr_details = fetch_pr_details(pr_number, repo)
    files = pr_details.get("files", [])
    
    workspace_path = Path(workspace) if workspace else Path.cwd()
    workspace_abs = workspace_path.resolve()
    
    valid_files = []
    for f in files:
        path = f.get("path", "")
        if path:
            full_path = workspace_path / path
            try:
                resolved = full_path.resolve()
                # Security check: ensure file is within workspace (prevent path traversal)
                try:
                    common = os.path.commonpath([str(resolved), str(workspace_abs)])
                    # Handle Windows case-insensitivity
                    if os.name == 'nt':
                        common = common.lower()
                        workspace_check = str(workspace_abs).lower()
                    else:
                        workspace_check = str(workspace_abs)
                    if common != workspace_check:
                        # File is outside workspace directory - skip
                        continue
                except ValueError:
                    # Paths on different drives (Windows)
                    continue
                
                if resolved.is_file():
                    valid_files.append(str(resolved))
            except (OSError, ValueError):
                # Handle path resolution errors
                pass
    
    return valid_files

import contextlib

@contextlib.contextmanager
def manage_pr_branch(pr_number: int, repo: Optional[str], workspace: Optional[str] = None, should_checkout: bool = False):
    """
    Context manager to handle PR branch checkout and restoration.
    
    Args:
        pr_number: PR number
        repo: Repository owner/name
        workspace: Workspace path
        should_checkout: Whether to attempt checkout
        
    Yields:
        Dictionary with 'success' and 'branch' keys
    """
    original_branch = None
    pr_branch_checked_out = False
    result = {"success": False, "branch": None}
    
    if should_checkout:
        try:
            original_branch = get_current_branch(workspace)
            if original_branch:
                print(f"  📝 Saved original branch: {original_branch}")
            
            checkout_res = checkout_pr_branch(pr_number, repo, workspace)
            if checkout_res["success"]:
                pr_branch_checked_out = True
                result = checkout_res
                yield result
            else:
                yield result
        except Exception as e:
            print(f"  ⚠️  Error during PR checkout setup: {e}")
            yield result
    else:
        yield result
        
    # Restoration logic
    if pr_branch_checked_out and original_branch:
        try:
            print(f"\n🔀 Restoring original branch: {original_branch}")
            if restore_branch(original_branch, workspace):
                print(f"  ✅ Restored to branch: {original_branch}")
            else:
                print(f"  ⚠️  Could not restore to branch: {original_branch}")
                print(f"      Please run 'git checkout {original_branch}' manually")
        except Exception as e:
            print(f"  ⚠️  Error restoring branch: {e}")
            print(f"      Please run 'git checkout {original_branch}' manually")
