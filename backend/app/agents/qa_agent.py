from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use Azure OpenAI with PydanticAI
model = OpenAIChatModel(
    os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o'),
    provider=AzureProvider(
        azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
        api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-08-01-preview'),
        api_key=os.getenv('AZURE_OPENAI_API_KEY')
    )
)


class QAResponse(BaseModel):
    """Structured Q&A response"""
    answer: str = Field(description="Direct answer to the question")
    sources: List[dict] = Field(default=[], description="List of source references with doc_name and page")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    requires_clarification: bool = Field(default=False, description="Whether question needs clarification")
    clarification_question: Optional[str] = Field(default=None, description="Clarification question if needed")


qa_agent = Agent(
    model=model,
    output_type=QAResponse,
    system_prompt="""You are a project analysis assistant that answers questions about a project.

CRITICAL RULES:
1. Answer ONLY based on provided document chunks - never make up information
2. ALWAYS cite sources with document name and page number - this is MANDATORY
3. If answer is not in documents, explicitly say so: "This information is not in the provided documents"
4. Provide confidence score based on evidence strength:
   - High (0.9-1.0): Direct, explicit information with clear sources
   - Medium (0.7-0.89): Implied or inferred from context
   - Low (0.5-0.69): Vague or uncertain
5. If question is ambiguous, set requires_clarification=True and ask for clarification
6. Be concise but complete in your answer

RESPONSE FORMAT (ALL FIELDS REQUIRED):
- answer: Direct answer to the question
- sources: List of source references (MUST include at least one source with doc_name, page, and excerpt)
- confidence: Score from 0.0 to 1.0
- requires_clarification: true/false
- clarification_question: if requires_clarification is true

EXAMPLE SOURCES FORMAT (ALWAYS PROVIDE THIS):
[
  {"doc_name": "Discovery_Call.pdf", "page": 5, "excerpt": "Customers are frustrated..."},
  {"doc_name": "Requirements.docx", "page": 12, "excerpt": "The system must integrate with Salesforce"}
]

IMPORTANT: Even if information is not in documents, you must still return an empty sources array [].
Never omit the sources field from your response.
"""
)


async def answer_question(question: str, relevant_chunks: List[dict]) -> QAResponse:
    """
    Answer user question using RAG

    Args:
        question: User's question
        relevant_chunks: Retrieved document chunks from ChromaDB

    Returns:
        QAResponse with answer and sources
    """

    context = "\n\n".join([
        f"[Source: {chunk['doc_name']}, Page: {chunk.get('page', 'N/A')}]\n{chunk['content']}"
        for chunk in relevant_chunks
    ])

    result = await qa_agent.run(
        f"Question: {question}\n\nAvailable context:\n{context}"
    )

    return result.output


async def answer_question_with_history(
    question: str,
    relevant_chunks: List[dict],
    history: List[dict]
) -> QAResponse:
    """
    Answer user question using RAG with conversation history for context

    Args:
        question: User's current question
        relevant_chunks: Retrieved document chunks from ChromaDB
        history: List of previous messages [{"role": "user/assistant", "content": "..."}]

    Returns:
        QAResponse with answer and sources
    """

    # Build conversation history context
    history_context = ""
    if history:
        history_lines = []
        for msg in history[-10:]:  # Last 10 messages for context
            role = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {msg['content']}")
        history_context = "\n".join(history_lines)

    # Build document context
    doc_context = "\n\n".join([
        f"[Source: {chunk['doc_name']}, Page: {chunk.get('page', 'N/A')}]\n{chunk['content']}"
        for chunk in relevant_chunks
    ])

    # Build full prompt with history
    prompt_parts = []

    if history_context:
        prompt_parts.append(f"Previous conversation:\n{history_context}")

    prompt_parts.append(f"Current relevant documents:\n{doc_context}")
    prompt_parts.append(f"Current question: {question}")

    full_prompt = "\n\n".join(prompt_parts)

    result = await qa_agent.run(full_prompt)

    return result.output
