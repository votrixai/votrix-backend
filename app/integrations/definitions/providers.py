"""
Provider metadata — static mapping of provider slugs to Provider objects.

Pure data, no logic.
"""

from app.models.integration import Provider, ProviderType

PROVIDERS = {
    "platform": Provider(slug="platform", name="Platform", type=ProviderType.PLATFORM),
    "composio": Provider(slug="composio", name="Composio", type=ProviderType.COMPOSIO),
    "custom":   Provider(slug="custom",   name="Custom",   type=ProviderType.CUSTOM),
}
