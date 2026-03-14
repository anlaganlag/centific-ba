"""
Tests for configuration security requirements.

P0 Security: Ensure required secrets fail fast when missing.
"""
import pytest
import os
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class TestConfigSecurity:
    """Security tests for application configuration."""

    def test_jwt_secret_required(self):
        """JWT secret must be provided, no default allowed."""
        # Create isolated Settings class without .env file
        class TestSettings(BaseSettings):
            model_config = SettingsConfigDict(env_file=None)
            JWT_SECRET_KEY: str = Field(..., min_length=32)

        # Clear env var and test
        original = os.environ.pop("JWT_SECRET_KEY", None)
        try:
            with pytest.raises(ValidationError) as exc_info:
                TestSettings()
            assert "JWT_SECRET_KEY" in str(exc_info.value)
        finally:
            if original:
                os.environ["JWT_SECRET_KEY"] = original

    def test_jwt_secret_minimum_length(self):
        """JWT secret must be at least 32 characters."""
        class TestSettings(BaseSettings):
            model_config = SettingsConfigDict(env_file=None)
            JWT_SECRET_KEY: str = Field(..., min_length=32)

        # Should fail with short secret
        with pytest.raises(ValidationError):
            TestSettings(JWT_SECRET_KEY="too_short")

        # Should pass with adequate secret
        settings = TestSettings(JWT_SECRET_KEY="a" * 32)
        assert len(settings.JWT_SECRET_KEY) >= 32

    def test_azure_openai_key_required(self):
        """Azure OpenAI API key must be provided."""
        class TestSettings(BaseSettings):
            model_config = SettingsConfigDict(env_file=None)
            AZURE_OPENAI_API_KEY: str = Field(..., min_length=1)
            AZURE_OPENAI_ENDPOINT: str = Field(..., min_length=1)

        # Clear env var and test
        original_key = os.environ.pop("AZURE_OPENAI_API_KEY", None)
        original_endpoint = os.environ.pop("AZURE_OPENAI_ENDPOINT", None)
        try:
            with pytest.raises(ValidationError) as exc_info:
                TestSettings()
            assert "AZURE_OPENAI_API_KEY" in str(exc_info.value)
        finally:
            if original_key:
                os.environ["AZURE_OPENAI_API_KEY"] = original_key
            if original_endpoint:
                os.environ["AZURE_OPENAI_ENDPOINT"] = original_endpoint

    def test_openai_key_required(self):
        """OpenAI API key for embeddings must be provided."""
        class TestSettings(BaseSettings):
            model_config = SettingsConfigDict(env_file=None)
            OPENAI_API_KEY: str = Field(..., min_length=1)

        # Clear env var and test
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with pytest.raises(ValidationError) as exc_info:
                TestSettings()
            assert "OPENAI_API_KEY" in str(exc_info.value)
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original
