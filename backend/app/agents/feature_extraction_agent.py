import asyncio
import json
import logging
from typing import List, Optional, Callable

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
import os
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI

from app.models.analysis import FeatureDraft, FeatureExtractionResult

load_dotenv()
logger = logging.getLogger(__name__)

def _build_model() -> OpenAIModel:
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

    return OpenAIModel(
        os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
        openai_client=AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY')),
    )


model = _build_model()


# ── Map phase: extract partial features from a single chunk ──

class ChunkFeatures(BaseModel):
    """Partial features extracted from a single document chunk."""
    features: List[FeatureDraft] = Field(description="Features found in this chunk (0-5)")
    chunk_summary: str = Field(description="Brief summary of what this chunk covers")


map_agent = Agent(
    model=model,
    result_type=ChunkFeatures,
    retries=3,
    model_settings={'max_tokens': 4096},
    system_prompt="""You are an expert Business Analyst extracting features from a document chunk.

TASK: Analyze this single document chunk and extract any distinct features/capabilities mentioned.

RULES:
1. Extract 0-5 features from this chunk (0 if the chunk has no feature-relevant content)
2. Each feature must have:
   - feature_id: Use TEMP-001, TEMP-002, etc. (will be renumbered later)
   - title: Clear, concise feature name
   - problem_statement: What problem this feature solves
   - benefit: Business benefit/value
   - business_process: Which business process this relates to
   - scope: Clear boundaries of what's in-scope
   - sources: Quote relevant excerpts from this chunk
3. Only extract what is actually described or implied in the chunk
4. If the chunk is about non-functional requirements, architecture, timelines, etc. — still extract
   those as features if they describe capabilities
5. If the chunk has no feature-relevant content (e.g., table of contents, references), return empty features list
"""
)


# ── Reduce phase: merge and deduplicate all partial features ──

reduce_agent = Agent(
    model=model,
    result_type=FeatureExtractionResult,
    retries=3,
    model_settings={'max_tokens': 4096},
    system_prompt="""You are an expert Business Analyst consolidating features from multiple document chunks.

TASK: You receive partial features extracted from different chunks of the same project documents.
Merge, deduplicate, and refine them into a final cohesive list.

RULES:
1. Output 3-15 distinct, non-overlapping features
2. Merge features that describe the same capability (combine their sources, pick best description)
3. Assign final feature IDs: F-001, F-002, etc.
4. Each feature must have all fields filled:
   - feature_id, title, problem_statement, benefit, business_process, scope, sources
5. Preserve source references — combine sources from merged features
6. Remove duplicates but keep the richest description
7. If two features are similar but distinct aspects, keep them separate with clear scope boundaries
8. Write a summary that captures the overall project scope
9. Order features by business importance (most critical first)
"""
)


async def extract_features(
    chunks: List[dict],
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> FeatureExtractionResult:
    """
    Map-Reduce feature extraction from document chunks.

    Args:
        chunks: List of {"content": str, "metadata": {"doc_name": str, "page": str}} dicts
        on_progress: Optional callback(current, total, message) for progress updates

    Returns:
        FeatureExtractionResult with merged/deduplicated features
    """
    if not chunks:
        return FeatureExtractionResult(features=[], summary="No document content to analyze.")

    total_chunks = len(chunks)
    logger.info(f"Map-Reduce extraction: {total_chunks} chunks")

    # ── MAP phase ──
    semaphore = asyncio.Semaphore(5)
    completed = 0
    all_partial_features: List[FeatureDraft] = []
    chunk_summaries: List[str] = []

    async def process_chunk(chunk: dict, idx: int) -> ChunkFeatures:
        nonlocal completed
        async with semaphore:
            doc_name = chunk.get("metadata", {}).get("doc_name", "unknown")
            page = chunk.get("metadata", {}).get("page", "?")
            content = chunk.get("content", "")

            if not content.strip():
                completed += 1
                return ChunkFeatures(features=[], chunk_summary="Empty chunk")

            result = await map_agent.run(
                f"Document: {doc_name} (page {page})\n\n{content}"
            )
            completed += 1
            if on_progress:
                on_progress(completed, total_chunks, f"Extracting features from chunk {completed}/{total_chunks}")
            logger.info(f"Map chunk {completed}/{total_chunks}: {len(result.output.features)} features from {doc_name} p{page}")
            return result.output

    tasks = [process_chunk(chunk, i) for i, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, Exception):
            logger.warning(f"Chunk processing failed: {r}")
            continue
        all_partial_features.extend(r.features)
        if r.chunk_summary:
            chunk_summaries.append(r.chunk_summary)

    logger.info(f"Map phase done: {len(all_partial_features)} partial features from {total_chunks} chunks")

    if not all_partial_features:
        return FeatureExtractionResult(
            features=[],
            summary="No features could be extracted from the documents."
        )

    # ── REDUCE phase ──
    if on_progress:
        on_progress(total_chunks, total_chunks, "Merging and deduplicating features...")

    # Build reduce input
    partial_json = json.dumps([f.model_dump() for f in all_partial_features], indent=2)
    summaries_text = "\n".join(f"- {s}" for s in chunk_summaries[:50])

    result = await reduce_agent.run(
        f"Chunk summaries:\n{summaries_text}\n\n"
        f"All partial features ({len(all_partial_features)} total):\n{partial_json}"
    )

    logger.info(f"Reduce phase done: {len(result.output.features)} final features")
    return result.output
