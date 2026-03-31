"""Build system messages from agent config and optional template files."""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"


def build_system_prompt(
    agent_config: dict,
    tool_names: list[str] | None = None,
) -> str:
    """Assemble the system prompt string.

    Concatenation order:
    1. Base template — loaded from prompts/templates/{template_name}.md
       (defaults to "default" if agent_config has no template_name)
    2. Agent instructions — agent_config["system_prompt"]
    3. Tool preamble — auto-generated from active tool names

    Returns a single concatenated string (sections separated by blank lines).
    """
    parts: list[str] = []

    template_name = agent_config.get("template_name") or "default"
    base = _load_template(template_name)
    if base:
        parts.append(base.strip())

    agent_prompt = agent_config.get("system_prompt") or ""
    if agent_prompt.strip():
        parts.append(agent_prompt.strip())

    if tool_names:
        parts.append(_build_tool_preamble(tool_names))

    return "\n\n".join(parts)


def _load_template(template_name: str) -> str | None:
    """Load a .md template file. Returns None if the file does not exist."""
    path = TEMPLATES_DIR / f"{template_name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _build_tool_preamble(tool_names: list[str]) -> str:
    """Generate a brief tool listing for the system prompt."""
    names = ", ".join(f"`{n}`" for n in tool_names)
    return f"You have access to the following tools: {names}."
