"""
Factory for quickly defining Composio-backed integrations.

Usage — add a new Composio app as an Integration in ~10 lines:

    from app.tools.composio.factory import make_composio_integration

    GITHUB = make_composio_integration(
        id="github",
        display_name="GitHub",
        description="Manage GitHub repositories, issues, and pull requests",
        app_id="GITHUB",                        # Composio app name (all-caps)
        tools=[
            # (tool_id,        description,            composio_action,          input_schema)
            ("create_issue",   "Create a GitHub issue", "GITHUB_CREATE_ISSUE",    {...}),
            ("list_issues",    "List issues in a repo", "GITHUB_LIST_ISSUES",     {...}),
        ],
    )

Then register it in app/tools/registry.py:

    from app.tools.composio.github import GITHUB
    REGISTRY[GITHUB.id] = GITHUB
"""

from typing import Any, Dict, List, Tuple

from app.models.tools import Integration, Tool

# (tool_id, human description, composio_action_name, json_schema)
ToolDef = Tuple[str, str, str, Dict[str, Any]]


def make_composio_integration(
    id: str,
    display_name: str,
    description: str,
    app_id: str,
    tools: List[ToolDef],
    deferred: bool = True,
) -> Integration:
    """Build an Integration backed by a Composio app.

    Args:
        id:           Internal slug, e.g. "github" (stable key used in AgentIntegration).
        display_name: Human-readable name shown in the UI.
        description:  One-sentence description of what this integration does.
        app_id:       Composio app identifier (all-caps), e.g. "GITHUB".
        tools:        List of (tool_id, description, composio_action, input_schema) tuples.
        deferred:     Keep True for Composio apps — schemas are loaded on demand via tool_search.
    """
    return Integration(
        id=id,
        display_name=display_name,
        description=description,
        provider_id="composio",
        provider_config={"app_id": app_id},
        deferred=deferred,
        tools=[
            Tool(
                id=t[0],
                name=t[0],
                description=t[1],
                input_schema=t[3],
                # tool-level override: tells the runtime which Composio action to call
                provider_config={"app_id": app_id, "action": t[2]},
            )
            for t in tools
        ],
    )
