"""Tests for GlobalToolset role-based tool vending."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.tools._toolset import ROLE_PERMISSIONS, GlobalToolset, resolve_role


def make_context(agent_name: str) -> object:
    """Create a mock ReadonlyContext with the given agent_name."""
    ctx = MagicMock()
    ctx.agent_name = agent_name
    return ctx


# ---------------------------------------------------------------------------
# 1. Tool count — default role returns all 42 tools
# ---------------------------------------------------------------------------


class TestToolCount:
    async def test_default_returns_all_42_tools(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(None)
        assert len(tools) == 42

    async def test_all_tool_names_unique(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(None)
        names = [t.name for t in tools]
        assert len(names) == len(set(names)), f"Duplicate tool names: {names}"


# ---------------------------------------------------------------------------
# 2. Role filtering
# ---------------------------------------------------------------------------


class TestRoleFiltering:
    async def test_planner_gets_15_tools(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(make_context("plan_agent"))  # type: ignore[arg-type]
        names = {t.name for t in tools}
        assert len(tools) == 15
        expected = {
            "file_read",
            "file_glob",
            "file_grep",
            "directory_list",
            "code_symbols",
            "run_diagnostics",
            "git_status",
            "git_diff",
            "git_log",
            "git_show",
            "web_fetch",
            "web_search",
            "todo_read",
            "todo_write",
            "todo_list",
        }
        assert names == expected

    async def test_coder_gets_27_tools(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(make_context("code_agent"))  # type: ignore[arg-type]
        assert len(tools) == 27

    async def test_reviewer_gets_15_tools(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(make_context("review_agent"))  # type: ignore[arg-type]
        names = {t.name for t in tools}
        assert len(tools) == 15
        # Reviewer has the same set as planner
        planner_tools = await toolset.get_tools(make_context("plan_agent"))  # type: ignore[arg-type]
        planner_names = {t.name for t in planner_tools}
        assert names == planner_names

    async def test_fixer_gets_22_tools(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(make_context("fix_agent"))  # type: ignore[arg-type]
        assert len(tools) == 22

    async def test_fixer_excludes_dangerous_tools(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(make_context("fix_agent"))  # type: ignore[arg-type]
        names = {t.name for t in tools}
        forbidden = {"http_request", "git_commit", "git_branch", "git_worktree", "git_apply"}
        assert names.isdisjoint(forbidden), f"Fixer has forbidden tools: {names & forbidden}"

    async def test_pm_prefix_gets_12_tools(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(make_context("pm_project1"))  # type: ignore[arg-type]
        names = {t.name for t in tools}
        assert len(tools) == 12
        expected = {
            "select_ready_batch",
            "escalate_to_director",
            "update_deliverable",
            "query_deliverables",
            "reorder_deliverables",
            "manage_dependencies",
            "task_create",
            "task_update",
            "task_query",
            "todo_read",
            "todo_write",
            "todo_list",
        }
        assert names == expected

    async def test_director_gets_12_tools(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(make_context("director"))  # type: ignore[arg-type]
        names = {t.name for t in tools}
        assert len(tools) == 12
        expected = {
            "escalate_to_ceo",
            "list_projects",
            "query_project_status",
            "override_pm",
            "get_project_context",
            "query_dependency_graph",
            "task_create",
            "task_update",
            "task_query",
            "todo_read",
            "todo_write",
            "todo_list",
        }
        assert names == expected


# ---------------------------------------------------------------------------
# 3. excluded_tools
# ---------------------------------------------------------------------------


class TestExcludedTools:
    async def test_excluded_tools_removed_from_coder(self) -> None:
        toolset = GlobalToolset(excluded_tools={"bash_exec"})
        tools = await toolset.get_tools(make_context("code_agent"))  # type: ignore[arg-type]
        names = {t.name for t in tools}
        assert "bash_exec" not in names
        assert len(tools) == 26  # 27 - 1

    async def test_excluded_tools_removed_from_default(self) -> None:
        toolset = GlobalToolset(excluded_tools={"bash_exec", "http_request"})
        tools = await toolset.get_tools(None)
        names = {t.name for t in tools}
        assert "bash_exec" not in names
        assert "http_request" not in names
        assert len(tools) == 40  # 42 - 2

    async def test_excluding_nonexistent_tool_is_harmless(self) -> None:
        toolset = GlobalToolset(excluded_tools={"nonexistent_tool"})
        tools = await toolset.get_tools(None)
        assert len(tools) == 42


# ---------------------------------------------------------------------------
# 4. resolve_role
# ---------------------------------------------------------------------------


class TestResolveRole:
    def test_plan_agent_maps_to_planner(self) -> None:
        assert resolve_role(make_context("plan_agent")) == "planner"  # type: ignore[arg-type]

    def test_code_agent_maps_to_coder(self) -> None:
        assert resolve_role(make_context("code_agent")) == "coder"  # type: ignore[arg-type]

    def test_review_agent_maps_to_reviewer(self) -> None:
        assert resolve_role(make_context("review_agent")) == "reviewer"  # type: ignore[arg-type]

    def test_fix_agent_maps_to_fixer(self) -> None:
        assert resolve_role(make_context("fix_agent")) == "fixer"  # type: ignore[arg-type]

    def test_director_maps_to_director(self) -> None:
        assert resolve_role(make_context("director")) == "director"  # type: ignore[arg-type]

    def test_pm_prefix_maps_to_pm(self) -> None:
        assert resolve_role(make_context("pm_something")) == "pm"  # type: ignore[arg-type]

    def test_pm_another_prefix_maps_to_pm(self) -> None:
        assert resolve_role(make_context("pm_project_xyz")) == "pm"  # type: ignore[arg-type]

    def test_unknown_agent_maps_to_default(self) -> None:
        assert resolve_role(make_context("unknown_agent")) == "default"  # type: ignore[arg-type]

    def test_none_context_maps_to_default(self) -> None:
        assert resolve_role(None) == "default"


# ---------------------------------------------------------------------------
# 5. Schema generation — FunctionTool wrapping
# ---------------------------------------------------------------------------


class TestSchemaGeneration:
    async def test_all_tools_have_name_and_description(self) -> None:
        toolset = GlobalToolset()
        tools = await toolset.get_tools(None)
        for tool in tools:
            assert tool.name, f"Tool missing name: {tool}"
            assert tool.name.isidentifier(), f"Tool name not valid identifier: {tool.name}"
            decl = tool._get_declaration()  # type: ignore[reportPrivateUsage]
            assert decl is not None, f"Tool '{tool.name}' returned None declaration"
            assert decl.description, f"Tool '{tool.name}' has empty description"

    async def test_tool_context_excluded_from_schema(self) -> None:
        """Tools with a tool_context param should not expose it in the schema."""
        toolset = GlobalToolset()
        tools = await toolset.get_tools(None)
        for tool in tools:
            decl = tool._get_declaration()  # type: ignore[reportPrivateUsage]
            if decl is not None and decl.parameters and decl.parameters.properties:
                param_names = list(decl.parameters.properties.keys())
                assert "tool_context" not in param_names, (
                    f"Tool '{tool.name}' exposes tool_context in schema"
                )

    async def test_tool_names_match_function_names(self) -> None:
        """FunctionTool.name should match the original function __name__."""
        toolset = GlobalToolset()
        tools = await toolset.get_tools(None)
        names = {t.name for t in tools}
        expected = ROLE_PERMISSIONS["default"]
        assert names == expected


# ---------------------------------------------------------------------------
# Sanity: ROLE_PERMISSIONS consistency
# ---------------------------------------------------------------------------


class TestRolePermissionsConsistency:
    def test_all_role_tool_names_exist_in_default(self) -> None:
        """Every tool in a specific role must exist in the default (full) set."""
        all_tools = ROLE_PERMISSIONS["default"]
        for role, perms in ROLE_PERMISSIONS.items():
            if role == "default":
                continue
            unknown = perms - all_tools
            assert not unknown, f"Role '{role}' references unknown tools: {unknown}"

    async def test_role_subsets_never_exceed_default(self) -> None:
        toolset = GlobalToolset()
        default_tools = await toolset.get_tools(None)
        default_count = len(default_tools)
        for role in ROLE_PERMISSIONS:
            if role == "default":
                continue
            assert len(ROLE_PERMISSIONS[role]) <= default_count, (
                f"Role '{role}' has more tools ({len(ROLE_PERMISSIONS[role])}) than default"
            )
