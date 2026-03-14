import asyncio
import json
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider
import os
from dotenv import load_dotenv

from app.models.analysis import SingleFeatureInterviewResult, InterviewResult, InterviewQuestion

load_dotenv()

model = OpenAIChatModel(
    os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o'),
    provider=AzureProvider(
        azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
        api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-08-01-preview'),
        api_key=os.getenv('AZURE_OPENAI_API_KEY')
    )
)

# Agent that processes ONE feature at a time
single_feature_interview_agent = Agent(
    model=model,
    output_type=SingleFeatureInterviewResult,
    retries=5,
    model_settings={'max_tokens': 4096},
    system_prompt="""You are an expert Business Analyst conducting a discovery interview.

TASK: Given ONE feature and the original document content, generate exactly 4
clarifying interview questions — one per question type.

RULES:
1. Generate exactly 4 questions for this feature:
   - question_id: Use the IDs provided in the prompt (e.g., Q-001 through Q-004)
   - feature_id: The feature ID provided
   - question: Clear, specific question
   - question_type: One of each: scope, edge_case, dependency, business_value
   - suggested_answer: Your best answer based on the documents (REQUIRED)
2. Question types — exactly one of each:
   - 1 scope question (clarifying boundaries)
   - 1 edge_case question (what happens when...)
   - 1 dependency question (integration/prerequisites)
   - 1 business_value question (priority/impact)
3. Suggested answers should cite document content when possible
4. If documents don't have a clear answer, suggest a reasonable default and note it

IMPORTANT: suggested_answer is REQUIRED for every question — it's used in auto mode.
"""
)


async def _interview_single_feature(
    feature: dict,
    document_content: str,
    q_id_start: int,
) -> list[InterviewQuestion]:
    """Generate 4 interview questions for a single feature."""
    q_ids = [f"Q-{str(q_id_start + i).zfill(3)}" for i in range(4)]

    result = await single_feature_interview_agent.run(
        f"Feature:\n{json.dumps(feature, indent=2)}\n\n"
        f"Use these question IDs: {', '.join(q_ids)}\n\n"
        f"Document context (summary):\n{document_content[:10000]}"
    )
    return result.output.questions


async def generate_interview(feature_drafts_json: str, document_content: str) -> InterviewResult:
    """
    Generate interview questions by processing each feature individually,
    then combining results.
    """
    features_data = json.loads(feature_drafts_json)

    semaphore = asyncio.Semaphore(3)
    all_questions: list[list[InterviewQuestion]] = []

    async def process_feature(feat: dict, idx: int) -> list[InterviewQuestion]:
        async with semaphore:
            q_start = idx * 4 + 1  # Q-001, Q-005, Q-009, etc.
            return await _interview_single_feature(feat, document_content, q_start)

    tasks = [process_feature(feat, i) for i, feat in enumerate(features_data)]
    results = await asyncio.gather(*tasks)

    combined = []
    for qs in results:
        combined.extend(qs)

    return InterviewResult(questions=combined)
