"""Command dispatcher for votrix_run tool.

Routes commands to handler modules by namespace.
"""

import re
import logging

from app.tools.handlers import bootstrap, fs, registry, search, fetch

logger = logging.getLogger(__name__)

HANDLER_MAP = {
    "registry": registry,
    "ls": fs,
    "bootstrap": bootstrap,
    "module": bootstrap,
    "connection": bootstrap,
    "search": search,
    "fetch": fetch,
}

POSITIONAL_HANDLERS = [
    (search.parse, search.run),
    (fetch.parse, fetch.run),
]


def _normalize(command: str) -> str:
    """Trim, first line only, collapse whitespace."""
    line = command.strip().split("\n")[0].strip()
    return re.sub(r"\s+", " ", line)


async def dispatch_command(command: str) -> str:
    cmd = _normalize(command)
    if not cmd:
        return "Error: empty command."

    ns = re.split(r"[.\s]", cmd)[0].lower()

    handler = HANDLER_MAP.get(ns)
    if handler:
        args = handler.parse(cmd)
        if args is None:
            return f"Error: unrecognized subcommand or wrong arguments under '{ns}'."
        return await handler.run(**args)

    for parse_fn, run_fn in POSITIONAL_HANDLERS:
        args = parse_fn(cmd)
        if args is not None:
            return await run_fn(**args)

    namespaces = ", ".join(sorted(HANDLER_MAP.keys()))
    return (
        f"Error: unknown command '{cmd[:60]}'. "
        f"Recognized namespaces: {namespaces}. "
        f"Read the relevant SKILL.md for available commands."
    )
