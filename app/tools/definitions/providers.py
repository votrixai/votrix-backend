"""
Provider metadata — static mapping of provider IDs to Provider objects.

Pure data, no logic.
"""

from app.models.tools import Provider, ProviderType

PROVIDERS = {
    "platform": Provider(id="platform", name="Platform", type=ProviderType.PLATFORM),
    "composio": Provider(id="composio", name="Composio", type=ProviderType.COMPOSIO),
    "custom":   Provider(id="custom",   name="Custom",   type=ProviderType.CUSTOM),
}
