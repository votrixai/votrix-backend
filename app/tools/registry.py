"""
Central tool registry — single source of truth for all Integrations and Providers.

To add a new integration:
  1. Write a file, e.g. app/tools/composio/github.py, using make_composio_integration()
  2. Import it here and add to REGISTRY.

REGISTRY is read-only at runtime; no DB required.
"""

from typing import Dict, List, Optional

from app.models.tools import Integration, Provider
from app.tools.definitions.platform_tools import PLATFORM_INTEGRATION
from app.tools.definitions.providers import PROVIDERS

# ---------------------------------------------------------------------------
# Default integrations pre-activated for every new org.
# platform is always available and not included here.
# ---------------------------------------------------------------------------
DEFAULT_ORG_INTEGRATIONS: List[str] = [
    # Google (all verified on composio.dev/toolkits/*)
    "gmail",
    "googlecalendar",
    "googlesheets",
    "googledocs",
    "googledrive",
    "googleads",
    "googlemeet",
    # Google My Business — slug unconfirmed, TODO verify
    # "googlemybusiness",
    # Meta (facebook slug is "facebook", covers Pages; instagram & whatsapp verified)
    "facebook",
    "instagram",
    "whatsapp",
    # Social (both verified)
    "twitter",
    "reddit",
    # SMB (all verified)
    "yelp",
    "notion",
    "stripe",
    "shopify",
]

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
