import pytest
from pydantic import SecretStr, ValidationError

from app.config.settings import Settings


def test_production_rejects_placeholder_secrets_and_legacy_api(
    test_settings: Settings,
) -> None:
    values = test_settings.model_dump()
    values.update(
        {
            "environment": "production",
            "debug": False,
            "legacy_api_enabled": False,
            "jwt_secret_key": SecretStr(
                "replace-with-an-independent-random-secret-at-least-32-bytes"
            ),
            "refresh_token_pepper": SecretStr(
                "a-real-looking-but-independent-refresh-pepper-123456"
            ),
        }
    )
    with pytest.raises(ValidationError):
        Settings.model_validate(values)

    values["jwt_secret_key"] = SecretStr(
        "production-jwt-secret-with-at-least-thirty-two-random-bytes"
    )
    values["legacy_api_enabled"] = True
    with pytest.raises(ValidationError):
        Settings.model_validate(values)
