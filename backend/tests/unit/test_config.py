import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://localhost:5173", ["http://localhost:5173"]),
        ("http://a.test, http://b.test", ["http://a.test", "http://b.test"]),
    ],
)
def test_cors_origins_accept_comma_separated_env(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: list[str]
) -> None:
    # The format used in backend/.env must load (it used to require JSON).
    monkeypatch.setenv("GG_CORS_ORIGINS", raw)
    assert Settings().cors_origins == expected


def test_api_key_is_never_printed() -> None:
    settings = Settings(anthropic_api_key="sk-ant-test-123")

    assert "sk-ant-test-123" not in repr(settings)
    assert "sk-ant-test-123" not in str(settings.model_dump())
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test-123"
