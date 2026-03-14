"""
Shared model factory for pydantic-ai agents.

Provides a centralized way to build OpenAI models with Azure or standard OpenAI support.
"""
import os
from dotenv import load_dotenv

from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncAzureOpenAI, AsyncOpenAI

load_dotenv()


def build_model() -> OpenAIModel:
    """
    Build an OpenAI model instance.

    Priority:
    1. Azure OpenAI (if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are set)
    2. Standard OpenAI (fallback)

    Returns:
        OpenAIModel: Configured model instance
    """
    azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    azure_api_key = os.getenv('AZURE_OPENAI_API_KEY')
    azure_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o')
    azure_api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')

    if azure_endpoint and azure_api_key:
        return OpenAIModel(
            azure_deployment,
            openai_client=AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_version=azure_api_version,
                api_key=azure_api_key,
            ),
        )

    # Fallback to standard OpenAI
    return OpenAIModel(
        os.getenv('OPENAI_MODEL', 'gpt-4o'),
        openai_client=AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY')),
    )


# Shared model instance
model = build_model()
