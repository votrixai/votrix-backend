"""Unit tests for app.storage — is_text_mime and helpers."""

from app.storage import is_text_mime


# ── is_text_mime ─────────────────────────────────────────────


def test_text_plain():
    assert is_text_mime("text/plain") is True


def test_text_html():
    assert is_text_mime("text/html") is True


def test_text_csv():
    assert is_text_mime("text/csv") is True


def test_text_markdown():
    assert is_text_mime("text/markdown") is True


def test_text_xml():
    assert is_text_mime("text/xml") is True


def test_text_x_python():
    assert is_text_mime("text/x-python") is True


def test_application_json():
    assert is_text_mime("application/json") is True


def test_application_yaml():
    assert is_text_mime("application/yaml") is True


def test_application_xml():
    assert is_text_mime("application/xml") is True


def test_application_javascript():
    assert is_text_mime("application/javascript") is True


def test_application_typescript():
    assert is_text_mime("application/typescript") is True


def test_application_sql():
    assert is_text_mime("application/sql") is True


def test_application_toml():
    assert is_text_mime("application/toml") is True


def test_application_x_sh():
    assert is_text_mime("application/x-sh") is True


def test_application_graphql():
    assert is_text_mime("application/graphql") is True


# ── Binary MIME types → False ────────────────────────────────


def test_image_png():
    assert is_text_mime("image/png") is False


def test_image_jpeg():
    assert is_text_mime("image/jpeg") is False


def test_application_pdf():
    assert is_text_mime("application/pdf") is False


def test_application_zip():
    assert is_text_mime("application/zip") is False


def test_application_octet_stream():
    assert is_text_mime("application/octet-stream") is False


def test_video_mp4():
    assert is_text_mime("video/mp4") is False


def test_audio_mpeg():
    assert is_text_mime("audio/mpeg") is False


def test_application_sqlite():
    assert is_text_mime("application/x-sqlite3") is False


def test_application_wasm():
    assert is_text_mime("application/wasm") is False


def test_font_woff2():
    assert is_text_mime("font/woff2") is False


# ── Edge cases ───────────────────────────────────────────────


def test_empty_string():
    assert is_text_mime("") is False


def test_charset_parameter():
    assert is_text_mime("text/plain; charset=utf-8") is True


def test_application_json_charset():
    assert is_text_mime("application/json; charset=utf-8") is True


def test_uppercase():
    assert is_text_mime("TEXT/PLAIN") is True


def test_mixed_case():
    assert is_text_mime("Application/JSON") is True


def test_whitespace():
    assert is_text_mime("  text/plain  ") is True
