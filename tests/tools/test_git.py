"""Tests for git tools."""

from pathlib import Path

from app.models.enums import GitBranchAction, GitWorktreeAction
from app.tools.git import (
    git_apply,
    git_branch,
    git_commit,
    git_diff,
    git_log,
    git_show,
    git_status,
    git_worktree,
)


async def test_git_status_clean(git_repo: Path) -> None:
    """Clean repo reports 'Clean'."""
    result = await git_status(str(git_repo))
    assert "Clean" in result


async def test_git_status_untracked(git_repo: Path) -> None:
    """Creating a file shows it as untracked."""
    (git_repo / "new.txt").write_text("new file\n")
    result = await git_status(str(git_repo))
    assert "new.txt" in result


async def test_git_commit_stages_and_commits(git_repo: Path) -> None:
    """Commit after creating a file returns a short hash."""
    (git_repo / "feature.txt").write_text("feature\n")
    result = await git_commit(str(git_repo), "add feature")
    # Result should be the short commit hash (alphanumeric, 7+ chars)
    assert len(result.strip()) >= 7
    # Repo should be clean afterwards
    status = await git_status(str(git_repo))
    assert "Clean" in status


async def test_git_commit_nothing_to_commit(git_repo: Path) -> None:
    """Committing on a clean repo returns 'Nothing to commit'."""
    result = await git_commit(str(git_repo), "empty")
    assert "Nothing to commit" in result


async def test_git_commit_selective_files(git_repo: Path) -> None:
    """Commit with selective files only stages specified files."""
    (git_repo / "a.txt").write_text("a\n")
    (git_repo / "b.txt").write_text("b\n")
    result = await git_commit(str(git_repo), "add a only", files=["a.txt"])
    assert len(result.strip()) >= 7
    # b.txt should still be untracked
    status = await git_status(str(git_repo))
    assert "b.txt" in status


async def test_git_branch_create(git_repo: Path) -> None:
    """CREATE action creates and switches to a new branch."""
    result = await git_branch(str(git_repo), "feature-x", GitBranchAction.CREATE)
    assert "Created" in result
    assert "feature-x" in result


async def test_git_branch_switch(git_repo: Path) -> None:
    """SWITCH action checks out an existing branch."""
    # Create a new branch (switches to it automatically)
    await git_branch(str(git_repo), "dev", GitBranchAction.CREATE)
    # Create another branch to switch away from dev
    await git_branch(str(git_repo), "other", GitBranchAction.CREATE)
    # Switch back to dev
    result = await git_branch(str(git_repo), "dev", GitBranchAction.SWITCH)
    assert "Switched" in result
    assert "dev" in result


async def test_git_branch_delete(git_repo: Path) -> None:
    """DELETE action removes a branch."""
    await git_branch(str(git_repo), "to-delete", GitBranchAction.CREATE)
    # Create a second branch to switch to (avoids needing to know initial branch name)
    await git_branch(str(git_repo), "safe", GitBranchAction.CREATE)
    result = await git_branch(str(git_repo), "to-delete", GitBranchAction.DELETE)
    assert "Deleted" in result
    assert "to-delete" in result


async def test_git_diff_shows_changes(git_repo: Path) -> None:
    """Diff shows actual content changes."""
    (git_repo / "hello.txt").write_text("Hello, changed!\n")
    result = await git_diff(str(git_repo))
    assert "changed" in result
    assert "Unstaged" in result


async def test_git_log_returns_history(git_repo: Path) -> None:
    """Log returns commit history respecting count."""
    # Create a second commit
    (git_repo / "log_test.txt").write_text("log\n")
    await git_commit(str(git_repo), "second commit")

    result = await git_log(str(git_repo), count=5)
    assert "Initial commit" in result
    assert "second commit" in result


async def test_git_show_displays_commit(git_repo: Path) -> None:
    """Show displays commit details for HEAD."""
    result = await git_show(str(git_repo), "HEAD")
    assert "Initial commit" in result


async def test_git_apply_patch(git_repo: Path) -> None:
    """Apply applies a unified diff patch correctly."""
    # Create a patch that modifies hello.txt
    patch = (
        "diff --git a/hello.txt b/hello.txt\n"
        "--- a/hello.txt\n"
        "+++ b/hello.txt\n"
        "@@ -1 +1 @@\n"
        "-Hello, world!\n"
        "+Hello, patched!\n"
    )
    result = await git_apply(str(git_repo), patch)
    assert "applied successfully" in result
    content = (git_repo / "hello.txt").read_text()
    assert "patched" in content


async def test_git_diff_with_ref(git_repo: Path) -> None:
    """Diff against a specific ref shows changes since that commit."""
    # Create a second commit
    (git_repo / "new.txt").write_text("new content\n")
    await git_commit(str(git_repo), "second commit")
    # Modify the file again (unstaged)
    (git_repo / "new.txt").write_text("modified content\n")
    result = await git_diff(str(git_repo), ref="HEAD")
    assert "modified" in result


async def test_git_diff_no_changes(git_repo: Path) -> None:
    """Diff on clean repo returns 'No differences'."""
    result = await git_diff(str(git_repo))
    assert "No differences" in result


# ---------------------------------------------------------------------------
# git_worktree lifecycle: ADD -> LIST -> REMOVE
# ---------------------------------------------------------------------------


async def test_git_worktree_add_list_remove(git_repo: Path) -> None:
    """Full worktree lifecycle: add, list, remove."""
    repo = str(git_repo)
    # Create branch without switching to it (git branch, not checkout -b)
    # Using checkout -b then switching back leaves git considering the branch
    # "in use" by the main worktree.
    from app.tools._shared import run_git

    _, _ = await run_git(["branch", "wt-branch"], cwd=repo)

    # ADD
    result = await git_worktree(repo, GitWorktreeAction.ADD, branch="wt-branch")
    assert "Worktree created" in result
    expected_path = str(Path(repo).parent / "worktree-wt-branch")
    assert expected_path in result
    assert Path(expected_path).is_dir()

    # LIST
    result = await git_worktree(repo, GitWorktreeAction.LIST)
    assert "worktree-wt-branch" in result

    # REMOVE
    result = await git_worktree(repo, GitWorktreeAction.REMOVE, branch="wt-branch")
    assert "Worktree removed" in result
    assert not Path(expected_path).is_dir()


async def test_git_worktree_add_missing_branch_returns_error(git_repo: Path) -> None:
    """ADD without branch returns an error."""
    result = await git_worktree(str(git_repo), GitWorktreeAction.ADD)
    assert "Branch name is required" in result


async def test_git_worktree_remove_missing_branch_returns_error(git_repo: Path) -> None:
    """REMOVE without branch returns an error."""
    result = await git_worktree(str(git_repo), GitWorktreeAction.REMOVE)
    assert "Branch name is required" in result


async def test_non_git_directory_error(tmp_path: Path) -> None:
    """Operations on non-git directories return an error."""
    result = await git_status(str(tmp_path))
    assert "Not a git repository" in result
