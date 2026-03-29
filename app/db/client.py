"""Supabase client singleton."""

from supabase import Client, create_client

_client: Client | None = None


def init_supabase(url: str, service_key: str) -> Client:
    global _client
    if not url or not service_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
    _client = create_client(url, service_key)
    return _client


def get_supabase() -> Client:
    if _client is None:
        raise RuntimeError("Supabase client not initialized. Call init_supabase() first.")
    return _client
