from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ── Enums ─────────────────────────────────────────────────

class QuestionType(str, Enum):
    scope = "scope"
    edge_case = "edge_case"
    dependency = "dependency"
    business_value = "business_value"


class AnalysisMode(str, Enum):
    auto = "auto"
    guided = "guided"


class AnalysisStatus(str, Enum):
    extracting = "extracting"
    interviewing = "interviewing"
    awaiting_answers = "awaiting_answers"
    generating = "generating"
    done = "done"
    error = "error"


# ── Step 1: Feature Extraction ────────────────────────────

class FeatureDraft(BaseModel):
    feature_id: str = Field(description="Unique identifier like F-001")
    title: str = Field(description="Short feature title")
    problem_statement: str = Field(description="What problem does this solve")
    benefit: str = Field(description="Business benefit of this feature")
    business_process: str = Field(description="Which business process this relates to")
    scope: str = Field(description="In-scope boundaries for this feature")
    sources: List[str] = Field(default=[], description="Source references from documents")


class FeatureExtractionResult(BaseModel):
    features: List[FeatureDraft] = Field(description="List of extracted features")
    summary: str = Field(description="Brief summary of the overall analysis")


# ── Step 2: Interview Q&A ────────────────────────────────

class InterviewQuestion(BaseModel):
    question_id: str = Field(description="Unique identifier like Q-001")
    feature_id: str = Field(description="Which feature this question relates to")
    question: str = Field(description="The interview question")
    question_type: QuestionType = Field(description="Type of question")
    suggested_answer: str = Field(description="AI-suggested answer based on documents")
    user_answer: Optional[str] = Field(default=None, description="User-provided answer (guided mode)")


class SingleFeatureInterviewResult(BaseModel):
    """Interview questions for a single feature."""
    questions: List[InterviewQuestion] = Field(description="4 interview questions for one feature")


class InterviewResult(BaseModel):
    questions: List[InterviewQuestion] = Field(description="List of interview questions")


# ── Step 3: Story Generation ─────────────────────────────

class AcceptanceCriterion(BaseModel):
    given: str = Field(description="Given precondition")
    when: str = Field(description="When action")
    then: str = Field(description="Then expected result")


class UserStory(BaseModel):
    story_id: str = Field(description="Unique identifier like US-001")
    as_a: str = Field(description="As a <role>")
    i_want: str = Field(description="I want <capability>")
    so_that: str = Field(description="So that <benefit>")
    acceptance_criteria: List[AcceptanceCriterion] = Field(description="Given/When/Then criteria")
    business_rules: List[str] = Field(default=[], description="Business rules for this story")
    dependencies: List[str] = Field(default=[], description="Dependencies on other features/stories")


class Feature(BaseModel):
    feature_id: str = Field(description="Matches feature_id from FeatureDraft")
    title: str
    problem_statement: str
    benefit: str
    business_process: str
    scope: str
    sources: List[str] = Field(default=[])
    user_stories: List[UserStory] = Field(description="Generated user stories for this feature")


class SingleFeatureResult(BaseModel):
    """Result for a single feature with its user stories."""
    feature: Feature = Field(description="Refined feature with user stories")


class StoryGenerationResult(BaseModel):
    features: List[Feature] = Field(description="Refined features with user stories")
    notes: str = Field(default="", description="Any additional notes from the analysis")


# ── API Request/Response Models ───────────────────────────

class StartAnalysisRequest(BaseModel):
    mode: AnalysisMode = Field(default=AnalysisMode.auto)


class SubmitAnswersRequest(BaseModel):
    answers: List[dict] = Field(description="List of {question_id, user_answer}")


class AnalysisStatusResponse(BaseModel):
    session_id: str
    project_id: str
    mode: str
    status: str
    error_message: Optional[str] = None
    progress_message: Optional[str] = None
    feature_drafts: Optional[List[FeatureDraft]] = None
    questions: Optional[List[InterviewQuestion]] = None
    features: Optional[List[Feature]] = None
