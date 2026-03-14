"""
Pytest configuration and fixtures.

Sets up test environment with mocked external services.
"""
import os
import sys
from unittest.mock import MagicMock

# Set test environment variables before importing app
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-api-key-for-testing-only")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key-for-testing")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-must-be-at-least-32-chars")
os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("ENVIRONMENT", "test")

# Mock pydantic_ai before app imports (pydantic-ai 0.0.14 has _griffe dependency issue)
mock_ai = MagicMock()
mock_models = MagicMock()
mock_providers = MagicMock()
sys.modules["pydantic_ai"] = mock_ai
sys.modules["pydantic_ai.models"] = mock_models
sys.modules["pydantic_ai.models.openai"] = mock_models.openai
sys.modules["pydantic_ai.providers"] = mock_providers
sys.modules["pydantic_ai.providers.azure"] = mock_providers.azure

import pytest
