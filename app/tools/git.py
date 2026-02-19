"""Git tools for repository operations.

All functions return descriptive strings and never raise exceptions.
ADK generates tool schemas from the function signatures and docstrings.
"""

import tempfile
from pathlib import Path

from app.lib.logging import get_logger
from app.models.enums import GitBranchAction, GitWorktreeAction
from app.tools._shared import run_git, truncate_output

logger = get_logger("tools.git")


def _validate_repo(path: str) -> str | None:
    """Return an error string if path is not a git repository, else None."""
    if not (Path(path) / ".git").exists():
        return f"Not a git repository: {path}"
    return None


async def git_status(path: str) -> str:
    """Current repository state.

    Returns a summary of staged, unstaged, and untracked changes,
    or 'Clean' if the working tree has no modifications.

    Args:
        path: Absolute path to the git repository root.
    """
    try:
        if err := _validate_repo(path):
            return err

        code, porcelain = await run_git(["status", "--porcelain"], cwd=path)
        if code != 0:
            return f"git status failed: {porcelain}"

        if not porcelain:
            return "Clean"

        _, short = await run_git(["status", "--short"], cwd=path)
        return short
    except Exception as exc:
        logger.exception("git_status error")
        return f"Error: {exc}"


async def git_commit(
    path: str,
    message: str,
    files: list[str] | None = None,
) -> str:
    """Stage and commit changes. Optional selective file staging.

    If files is provided, stages only those files. Otherwise stages all
    changes with 'git add -A'. Returns the commit hash on success.

    Args:
        path: Absolute path to the git repository root.
        message: Commit message.
        files: Optional list of file paths to stage. Stages all if omitted.
    """
    try:
        if err := _validate_repo(path):
            return err

        # Check if there is anything to commit
        code, porcelain = await run_git(["status", "--porcelain"], cwd=path)
        if code != 0:
            return f"git status failed: {porcelain}"
        if not porcelain:
            return "Nothing to commit"

        # Stage files
        if files is not None:
            for f in files:
                add_code, add_out = await run_git(["add", f], cwd=path)
                if add_code != 0:
                    return f"git add failed for {f}: {add_out}"
        else:
            add_code, add_out = await run_git(["add", "-A"], cwd=path)
            if add_code != 0:
                return f"git add -A failed: {add_out}"

        # Commit
        code, output = await run_git(["commit", "-m", message], cwd=path)
        if code != 0:
            return f"git commit failed: {output}"

        # Extract commit hash
        hash_code, hash_out = await run_git(["rev-parse", "--short", "HEAD"], cwd=path)
        if hash_code == 0:
            return hash_out
        return output
    except Exception as exc:
        logger.exception("git_commit error")
        return f"Error: {exc}"


async def git_branch(
    path: str,
    name: str,
    action: GitBranchAction,
) -> str:
    """Create, switch, or delete branches.

    Args:
        path: Absolute path to the git repository root.
        name: Branch name.
        action: CREATE to create and switch, SWITCH to checkout,
                DELETE to delete the branch.
    """
    try:
        if err := _validate_repo(path):
            return err

        if action == GitBranchAction.CREATE:
            code, output = await run_git(["checkout", "-b", name], cwd=path)
            if code != 0:
                # Idempotent: branch may already exist
                if "already exists" in output:
                    return f"Branch '{name}' already exists"
                return f"git checkout -b failed: {output}"
            return f"Created and switched to branch '{name}'"

        if action == GitBranchAction.SWITCH:
            code, output = await run_git(["checkout", name], cwd=path)
            if code != 0:
                return f"git checkout failed: {output}"
            return f"Switched to branch '{name}'"

        if action == GitBranchAction.DELETE:
            code, output = await run_git(["branch", "-d", name], cwd=path)
            if code != 0:
                return f"git branch -d failed: {output}"
            return f"Deleted branch '{name}'"

        return f"Unknown action: {action}"
    except Exception as exc:
        logger.exception("git_branch error")
        return f"Error: {exc}"


async def git_diff(path: str, ref: str | None = None) -> str:
    """Show changes against a reference.

    Without ref, shows both unstaged and staged changes.
    With ref, shows diff against that ref (branch, tag, or commit).

    Args:
        path: Absolute path to the git repository root.
        ref: Optional git ref to diff against (branch, tag, or commit SHA).
    """
    try:
        if err := _validate_repo(path):
            return err

        if ref is not None:
            code, output = await run_git(["diff", ref], cwd=path)
            if code != 0:
                return f"git diff failed: {output}"
            return truncate_output(output) if output else "No differences"

        # Unstaged changes
        code, unstaged = await run_git(["diff"], cwd=path)
        if code != 0:
            return f"git diff failed: {unstaged}"

        # Staged changes
        code, staged = await run_git(["diff", "--cached"], cwd=path)
        if code != 0:
            return f"git diff --cached failed: {staged}"

        parts: list[str] = []
        if unstaged:
            parts.append(f"=== Unstaged ===\n{unstaged}")
        if staged:
            parts.append(f"=== Staged ===\n{staged}")

        if not parts:
            return "No differences"

        return truncate_output("\n\n".join(parts))
    except Exception as exc:
        logger.exception("git_diff error")
        return f"Error: {exc}"


async def git_log(
    path: str,
    count: int | None = None,
    ref: str | None = None,
) -> str:
    """Show commit history with optional count limit and ref filter.

    Args:
        path: Absolute path to the git repository root.
        count: Maximum number of commits to show. Defaults to 10.
        ref: Optional git ref to start from (branch, tag, or commit SHA).
    """
    try:
        if err := _validate_repo(path):
            return err

        effective_count = count if count is not None else 10
        args = ["log", "--oneline", "-n", str(effective_count)]
        if ref is not None:
            args.append(ref)

        code, output = await run_git(args, cwd=path)
        if code != 0:
            return f"git log failed: {output}"

        return truncate_output(output) if output else "No commits"
    except Exception as exc:
        logger.exception("git_log error")
        return f"Error: {exc}"


async def git_show(path: str, ref: str) -> str:
    """Inspect a specific commit (message, diff, metadata).

    Args:
        path: Absolute path to the git repository root.
        ref: Git ref to show (commit SHA, tag, or branch name).
    """
    try:
        if err := _validate_repo(path):
            return err

        code, output = await run_git(["show", ref], cwd=path)
        if code != 0:
            return f"git show failed: {output}"

        return truncate_output(output)
    except Exception as exc:
        logger.exception("git_show error")
        return f"Error: {exc}"


async def git_worktree(
    path: str,
    action: GitWorktreeAction,
    branch: str | None = None,
) -> str:
    """Manage git worktrees for parallel execution across branches.

    Supports adding, listing, and removing worktrees. Worktrees are
    created as siblings of the repository at ../worktree-{branch}.

    Args:
        path: Absolute path to the git repository root.
        action: ADD to create, LIST to show all, REMOVE to delete a worktree.
        branch: Branch name (required for ADD and REMOVE).
    """
    try:
        if err := _validate_repo(path):
            return err

        if action == GitWorktreeAction.LIST:
            code, output = await run_git(["worktree", "list"], cwd=path)
            if code != 0:
                return f"git worktree list failed: {output}"
            return output

        if action == GitWorktreeAction.ADD:
            if branch is None:
                return "Branch name is required for ADD action"
            worktree_path = str(Path(path).parent / f"worktree-{branch}")
            code, output = await run_git(["worktree", "add", worktree_path, branch], cwd=path)
            if code != 0:
                return f"git worktree add failed: {output}"
            return f"Worktree created at {worktree_path}"

        if action == GitWorktreeAction.REMOVE:
            if branch is None:
                return "Branch name is required for REMOVE action"
            worktree_path = str(Path(path).parent / f"worktree-{branch}")
            code, output = await run_git(["worktree", "remove", worktree_path], cwd=path)
            if code != 0:
                return f"git worktree remove failed: {output}"
            return f"Worktree removed: {worktree_path}"

        return f"Unknown action: {action}"
    except Exception as exc:
        logger.exception("git_worktree error")
        return f"Error: {exc}"


async def git_apply(path: str, patch: str) -> str:
    """Apply a unified diff patch to the working tree.

    Writes the patch content to a temporary file and applies it
    with 'git apply'. The temporary file is cleaned up afterward.

    Args:
        path: Absolute path to the git repository root.
        patch: Unified diff patch content to apply.
    """
    try:
        if err := _validate_repo(path):
            return err

        # Write patch to a temp file
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".patch",
                delete=False,
            ) as tmp:
                tmp.write(patch)
                tmp_path = tmp.name

            code, output = await run_git(["apply", tmp_path], cwd=path)
            if code != 0:
                return f"git apply failed: {output}"

            return "Patch applied successfully"
        finally:
            if tmp_path is not None:
                Path(tmp_path).unlink(missing_ok=True)
    except Exception as exc:
        logger.exception("git_apply error")
        return f"Error: {exc}"
