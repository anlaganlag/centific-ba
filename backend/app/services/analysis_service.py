import asyncio
import json
import uuid
import logging
from typing import Optional, List
from datetime import datetime

from app.services.db_service import DatabaseService
from app.services.vector_service import VectorService
from app.models.analysis import (
    AnalysisMode, AnalysisStatus,
    FeatureExtractionResult, InterviewResult, StoryGenerationResult,
    AnalysisStatusResponse,
)
from app.agents.feature_extraction_agent import extract_features
from app.agents.interview_agent import generate_interview
from app.agents.story_generation_agent import generate_stories

logger = logging.getLogger(__name__)

# Truncated context for interview/story agents (they get features + limited doc context)
MAX_CONTEXT_FOR_SUBSTEPS = 15_000


class AnalysisService:
    """Orchestrates the 3-step BA analysis chain."""

    def __init__(self, db: DatabaseService):
        self.db = db

    def _get_chunks(self, project_id: str) -> List[dict]:
        """Get all document chunks from ChromaDB for this project."""
        vector_service = VectorService()
        return vector_service.get_all_documents(project_id)

    def _get_truncated_context(self, project_id: str) -> str:
        """Get truncated document context for interview/story agents."""
        docs = self.db.get_documents_by_project(project_id)
        parts = []
        total = 0
        for doc in docs:
            md = doc.get("cached_markdown") or ""
            if not md:
                continue
            header = f"\n\n--- Document: {doc['filename']} ---\n\n"
            if total + len(header) + len(md) > MAX_CONTEXT_FOR_SUBSTEPS:
                remaining = MAX_CONTEXT_FOR_SUBSTEPS - total - len(header)
                if remaining > 0:
                    parts.append(header + md[:remaining])
                break
            parts.append(header + md)
            total += len(header) + len(md)
        return "".join(parts)

    def _update_progress(self, session_id: str, message: str):
        """Update progress message in DB for frontend polling."""
        self.db.update_analysis_session(session_id, progress_message=message)

    async def start_analysis(self, project_id: str, mode: AnalysisMode) -> AnalysisStatusResponse:
        """
        Create session and launch analysis as a background task.
        Returns immediately with session_id so frontend can poll.
        """
        session_id = str(uuid.uuid4())
        self.db.create_analysis_session(session_id, project_id, mode.value)

        # Check documents exist
        chunks = self._get_chunks(project_id)
        if not chunks:
            self.db.update_analysis_session(
                session_id, status=AnalysisStatus.error.value,
                error_message="No documents found for this project. Upload documents first."
            )
            return self._build_response(session_id)

        # Launch background task
        asyncio.create_task(self._run_analysis(session_id, project_id, mode, chunks))

        return self._build_response(session_id)

    async def _run_analysis(
        self,
        session_id: str,
        project_id: str,
        mode: AnalysisMode,
        chunks: List[dict],
    ):
        """Background analysis pipeline."""
        try:
            # Step 1: Map-Reduce feature extraction
            self.db.update_analysis_session(
                session_id,
                status=AnalysisStatus.extracting.value,
                progress_message=f"Extracting features from {len(chunks)} chunks..."
            )

            def on_extract_progress(current: int, total: int, msg: str):
                self._update_progress(session_id, msg)

            extraction_result: FeatureExtractionResult = await extract_features(
                chunks, on_progress=on_extract_progress
            )
            feature_drafts_json = json.dumps([f.model_dump() for f in extraction_result.features])
            self.db.update_analysis_session(
                session_id,
                feature_drafts_json=feature_drafts_json,
                progress_message=f"Extracted {len(extraction_result.features)} features"
            )
            logger.info(f"Session {session_id}: Extracted {len(extraction_result.features)} features")

            # Step 2: Interview questions (per-feature, uses truncated context)
            self.db.update_analysis_session(
                session_id,
                status=AnalysisStatus.interviewing.value,
                progress_message="Generating interview questions..."
            )
            truncated_context = self._get_truncated_context(project_id)
            interview_result: InterviewResult = await generate_interview(
                feature_drafts_json, truncated_context
            )
            questions_json = json.dumps([q.model_dump() for q in interview_result.questions])
            self.db.update_analysis_session(
                session_id,
                questions_json=questions_json,
                progress_message=f"Generated {len(interview_result.questions)} interview questions"
            )
            logger.info(f"Session {session_id}: Generated {len(interview_result.questions)} questions")

            if mode == AnalysisMode.guided:
                self.db.update_analysis_session(
                    session_id,
                    status=AnalysisStatus.awaiting_answers.value,
                    progress_message="Waiting for your review of interview answers"
                )
                return

            # Auto mode: use suggested_answer as user_answer
            questions_with_answers = []
            for q in interview_result.questions:
                q_dict = q.model_dump()
                q_dict["user_answer"] = q_dict["suggested_answer"]
                questions_with_answers.append(q_dict)
            answered_json = json.dumps(questions_with_answers)
            self.db.update_analysis_session(session_id, questions_json=answered_json)

            # Step 3: Story generation (per-feature, uses truncated context)
            self.db.update_analysis_session(
                session_id,
                status=AnalysisStatus.generating.value,
                progress_message="Generating user stories..."
            )
            story_result: StoryGenerationResult = await generate_stories(
                feature_drafts_json, answered_json, truncated_context
            )

            total_stories = sum(len(f.user_stories) for f in story_result.features)
            self.db.update_analysis_session(
                session_id,
                status=AnalysisStatus.done.value,
                features_json=json.dumps([f.model_dump() for f in story_result.features]),
                progress_message=f"Done — {len(story_result.features)} features, {total_stories} user stories"
            )
            logger.info(f"Session {session_id}: Done — {len(story_result.features)} features, {total_stories} stories")

        except Exception as e:
            logger.exception(f"Session {session_id} failed: {e}")
            self.db.update_analysis_session(
                session_id,
                status=AnalysisStatus.error.value,
                error_message=str(e)
            )

    async def submit_answers_and_generate(
        self, session_id: str, answers: list[dict]
    ) -> AnalysisStatusResponse:
        """Guided mode: accept user answers and run step 3 in background."""
        session = self.db.get_analysis_session(session_id)
        if not session:
            raise ValueError("Session not found")
        if session["status"] != AnalysisStatus.awaiting_answers.value:
            raise ValueError(f"Session is not awaiting answers (status: {session['status']})")

        # Merge user answers into questions
        questions = json.loads(session["questions_json"] or "[]")
        answer_map = {a["question_id"]: a["user_answer"] for a in answers}
        for q in questions:
            if q["question_id"] in answer_map:
                q["user_answer"] = answer_map[q["question_id"]]
            else:
                q["user_answer"] = q.get("user_answer") or q["suggested_answer"]

        answered_json = json.dumps(questions)
        self.db.update_analysis_session(session_id, questions_json=answered_json)

        # Launch step 3 in background
        asyncio.create_task(
            self._run_story_generation(session_id, session["project_id"], session["feature_drafts_json"], answered_json)
        )

        # Return immediately
        return self._build_response(session_id)

    async def _run_story_generation(
        self, session_id: str, project_id: str, feature_drafts_json: str, answered_json: str
    ):
        """Background step 3 for guided mode."""
        try:
            self.db.update_analysis_session(
                session_id,
                status=AnalysisStatus.generating.value,
                progress_message="Generating user stories..."
            )
            truncated_context = self._get_truncated_context(project_id)
            story_result: StoryGenerationResult = await generate_stories(
                feature_drafts_json, answered_json, truncated_context
            )
            total_stories = sum(len(f.user_stories) for f in story_result.features)
            self.db.update_analysis_session(
                session_id,
                status=AnalysisStatus.done.value,
                features_json=json.dumps([f.model_dump() for f in story_result.features]),
                progress_message=f"Done — {len(story_result.features)} features, {total_stories} user stories"
            )
        except Exception as e:
            logger.exception(f"Story generation failed for session {session_id}: {e}")
            self.db.update_analysis_session(
                session_id,
                status=AnalysisStatus.error.value,
                error_message=str(e)
            )

    def get_status(self, project_id: str) -> Optional[AnalysisStatusResponse]:
        """Get latest analysis session for a project."""
        session = self.db.get_latest_analysis_session(project_id)
        if not session:
            return None
        return self._build_response_from_session(session)

    def _build_response(self, session_id: str) -> AnalysisStatusResponse:
        session = self.db.get_analysis_session(session_id)
        return self._build_response_from_session(session)

    def _build_response_from_session(self, session: dict) -> AnalysisStatusResponse:
        return AnalysisStatusResponse(
            session_id=session["id"],
            project_id=session["project_id"],
            mode=session["mode"],
            status=session["status"],
            error_message=session.get("error_message"),
            progress_message=session.get("progress_message"),
            feature_drafts=json.loads(session["feature_drafts_json"]) if session.get("feature_drafts_json") else None,
            questions=json.loads(session["questions_json"]) if session.get("questions_json") else None,
            features=json.loads(session["features_json"]) if session.get("features_json") else None,
        )
