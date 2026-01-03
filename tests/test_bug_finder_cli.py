
import os
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from bug_finder.cli import _safe_relative_to, _format_worker_results, get_git_changed_files

class TestCliUtils:
    def test_safe_relative_to_success(self, tmp_path):
        base = tmp_path
        child = base / "child" / "file.txt"
        
        rel = _safe_relative_to(child, base)
        assert rel == str(Path("child/file.txt"))

    def test_safe_relative_to_failure(self, tmp_path):
        base = tmp_path
        other = Path("/other/path/file.txt")
        
        # When relative_to fails, it should return the string of absolute path
        rel = _safe_relative_to(other, base)
        assert rel == str(other)

    def test_format_worker_results(self):
        worker_results = {
            "agent_results": [
                {
                    "role": "Agent A",
                    "success": True,
                    "response": "Found a bug."
                },
                {
                    "role": "Agent B",
                    "success": False,
                    "error": "Timeout"
                }
            ]
        }
        
        formatted = _format_worker_results(worker_results)
        assert "### Agent A" in formatted
        assert "Found a bug." in formatted
        assert "### Agent B" in formatted
        assert "[FAILED: Timeout]" in formatted

class TestGitUtils:
    @patch("bug_finder.cli.subprocess.run")
    def test_get_git_changed_files_not_repo(self, mock_run, tmp_path):
        # Simulate not a git repo
        mock_run.side_effect = subprocess.CalledProcessError(128, "git")
        
        files = get_git_changed_files(tmp_path)
        assert files == []

    @patch("bug_finder.cli.subprocess.run")
    def test_get_git_changed_files_success(self, mock_run, tmp_path):
        # Setup mocks for successful git executions
        
        # 1. is-inside-work-tree
        mock_is_repo = MagicMock()
        mock_is_repo.returncode = 0
        
        # 2. verify HEAD (Simulate existing repo)
        mock_head = MagicMock()
        mock_head.returncode = 0
        
        # 3. diff
        mock_diff = MagicMock()
        mock_diff.returncode = 0
        mock_diff.stdout = "file1.py\nsrc/file2.py"
        
        # 4. untracked
        mock_untracked = MagicMock()
        mock_untracked.returncode = 0
        mock_untracked.stdout = "new_file.py"
        
        mock_run.side_effect = [mock_is_repo, mock_head, mock_diff, mock_untracked]
        
        # We need to create the files so they pass the existence check in get_git_changed_files
        (tmp_path / "file1.py").touch()
        (tmp_path / "src").mkdir()
        (tmp_path / "src/file2.py").touch()
        (tmp_path / "new_file.py").touch()
        
        files = get_git_changed_files(tmp_path)
        
        # It dedups and resolves to absolute paths
        expected = {
            str((tmp_path / "file1.py").resolve()),
            str((tmp_path / "src/file2.py").resolve()),
            str((tmp_path / "new_file.py").resolve())
        }
        
        assert set(files) == expected
