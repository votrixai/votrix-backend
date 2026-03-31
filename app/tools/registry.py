"""
Central tool registry — single source of truth for all Integrations and Providers.

To add a new integration:
  1. Write a file, e.g. app/tools/composio/github.py, using make_composio_integration()
  2. Import it here and add to REGISTRY.

REGISTRY is read-only at runtime; no DB required.
"""

from typing import Dict, List, Optional

from app.models.tools import Integration, Provider
from app.tools.platform.schemas import PLATFORM_INTEGRATION, PROVIDERS as _PLATFORM_PROVIDERS

# ---------------------------------------------------------------------------
# All known providers (imported from platform schemas, extended here)
# ---------------------------------------------------------------------------
PROVIDERS: Dict[str, Provider] = dict(_PLATFORM_PROVIDERS)

# ---------------------------------------------------------------------------
# All known integrations
# ---------------------------------------------------------------------------
REGISTRY: Dict[str, Integration] = {
    PLATFORM_INTEGRATION.id: PLATFORM_INTEGRATION,
    # Add Composio-backed integrations below as you write them:
    # from app.tools.composio.github import GITHUB
    # GITHUB.id: GITHUB,
    # from app.tools.composio.google_calendar import GOOGLE_CALENDAR
    # GOOGLE_CALENDAR.id: GOOGLE_CALENDAR,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_integration(integration_id: str) -> Optional[Integration]:
    return REGISTRY.get(integration_id)


def list_integrations() -> List[Integration]:
    return list(REGISTRY.values())


def get_provider(provider_id: str) -> Optional[Provider]:
    return PROVIDERS.get(provider_id)
