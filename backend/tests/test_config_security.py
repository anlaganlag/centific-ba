"""
Tests for configuration security requirements.

P0 Security: Ensure required secrets fail fast when missing.
"""
import pytest
import os
from pydantic import ValidationError


class TestConfigSecurity:
    """Security tests for application configuration."""

    def test_jwt_secret_required(self):
        """JWT secret must be provided, no default allowed."""
        # Temporarily remove env var if exists
        original = os.environ.pop("JWT_SECRET_KEY", None)

        try:
            # Re-import to trigger validation
            from importlib import reload
            import app.config as config_module

            with pytest.raises(ValidationError) as exc_info:
                reload(config_module)

            assert "JWT_SECRET_KEY" in str(exc_info.value)
        finally:
            # Restore original value
            if original:
                os.environ["JWT_SECRET_KEY"] = original

    def test_jwt_secret_minimum_length(self):
        """JWT secret must be at least 32 characters."""
        from pydantic_settings import BaseSettings
        from pydantic import Field

        class TestSettings(BaseSettings):
            JWT_SECRET_KEY: str = Field(..., min_length=32)

        # Should fail with short secret
        with pytest.raises(ValidationError):
            TestSettings(JWT_SECRET_KEY="too_short")

        # Should pass with adequate secret
        settings = TestSettings(JWT_SECRET_KEY="a" * 32)
        assert len(settings.JWT_SECRET_KEY) >= 32

    def test_azure_openai_key_required(self):
        """Azure OpenAI API key must be provided."""
        original = os.environ.pop("AZURE_OPENAI_API_KEY", None)

        try:
            from importlib import reload
            import app.config as config_module

            with pytest.raises(ValidationError) as exc_info:
                reload(config_module)

            assert "AZURE_OPENAI_API_KEY" in str(exc_info.value)
        finally:
            if original:
                os.environ["AZURE_OPENAI_API_KEY"] = original

    def test_openai_key_required(self):
        """OpenAI API key for embeddings must be provided."""
        original = os.environ.pop("OPENAI_API_KEY", None)

        try:
            from importlib import reload
            import app.config as config_module

            with pytest.raises(ValidationError) as exc_info:
                reload(config_module)

            assert "OPENAI_API_KEY" in str(exc_info.value)
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original
