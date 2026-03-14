import asyncio
import json
from pydantic_ai import Agent

from app.models.analysis import StoryGenerationResult, Feature
from app.agents.model_factory import model

# Agent that processes ONE feature at a time to avoid output token limits
single_feature_agent = Agent(
    model=model,
    result_type=Feature,
    retries=5,
    model_settings={'max_tokens': 4096},
    system_prompt="""You are an expert Business Analyst generating user stories for a single feature.

TASK: Given ONE feature draft, its related interview Q&A, and document context,
generate detailed user stories with acceptance criteria for that feature.

RULES:
1. Generate 2-4 user stories for this feature
2. Each user story must have:
   - story_id: Use the IDs provided in the prompt (e.g., US-001, US-002)
   - as_a: Role (e.g., "admin user", "customer", "system")
   - i_want: Desired capability
   - so_that: Business benefit
   - acceptance_criteria: 2-3 criteria in Given/When/Then format
   - business_rules: Any relevant business rules (can be empty list)
   - dependencies: References to other features if applicable (can be empty list)
3. Refine feature details based on interview answers:
   - Update problem_statement if answers clarified the problem
   - Update scope if boundaries were clarified
   - Keep sources from original feature
4. Acceptance criteria must be testable and specific
5. Given/When/Then must be concrete and testable
"""
)


async def _generate_for_single_feature(
    feature_draft: dict,
    related_questions: list[dict],
    document_content: str,
    story_id_start: int,
) -> Feature:
    """Generate stories for a single feature."""
    story_ids = [f"US-{str(story_id_start + i).zfill(3)}" for i in range(5)]

    result = await single_feature_agent.run(
        f"Feature:\n{json.dumps(feature_draft, indent=2)}\n\n"
        f"Interview Q&A for this feature:\n{json.dumps(related_questions, indent=2)}\n\n"
        f"Use these story IDs: {', '.join(story_ids)}\n\n"
        f"Document context (summary):\n{document_content[:10000]}"
    )
    return result.output


async def generate_stories(
    feature_drafts_json: str,
    answered_questions_json: str,
    document_content: str
) -> StoryGenerationResult:
    """
    Generate user stories by processing each feature individually,
    then combining results. This avoids output token limits.
    """
    features_data = json.loads(feature_drafts_json)
    questions_data = json.loads(answered_questions_json)

    # Group questions by feature_id
    questions_by_feature: dict[str, list[dict]] = {}
    for q in questions_data:
        fid = q.get("feature_id", "")
        if fid not in questions_by_feature:
            questions_by_feature[fid] = []
        questions_by_feature[fid].append(q)

    # Process each feature concurrently (max 3 at a time to avoid rate limits)
    semaphore = asyncio.Semaphore(3)
    all_features: list[Feature] = []

    async def process_feature(feat: dict, idx: int) -> Feature:
        async with semaphore:
            fid = feat.get("feature_id", "")
            related_qs = questions_by_feature.get(fid, [])
            story_start = idx * 5 + 1  # US-001, US-006, US-011, etc.
            return await _generate_for_single_feature(
                feat, related_qs, document_content, story_start
            )

    tasks = [process_feature(feat, i) for i, feat in enumerate(features_data)]
    all_features = await asyncio.gather(*tasks)

    return StoryGenerationResult(
        features=list(all_features),
        notes=f"Generated stories for {len(all_features)} features."
    )
