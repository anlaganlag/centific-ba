"""
BA Toolkit API integration tests.

Uses FastAPI TestClient with isolated temp directories for DB and vector storage.
Tests that depend on external AI services (OpenAI embeddings, Azure OpenAI)
are skipped when API keys are not configured.
"""

import io
import os
import shutil
import tempfile
import unittest.mock as mock

import pytest
from fastapi.testclient import TestClient

from app.models.analysis import (
    FeatureDraft, FeatureExtractionResult,
    InterviewQuestion, SingleFeatureInterviewResult,
    Feature, UserStory, AcceptanceCriterion,
    StoryGenerationResult, QuestionType
)
from app.agents.feature_extraction_agent import ChunkFeatures


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def mock_external_services():
    """Mock OpenAI embeddings and Pydantic AI agents globally for tests."""
    with mock.patch("app.services.vector_service.VectorService.get_embedding_async", new_callable=mock.AsyncMock) as mock_emb_async, \
         mock.patch("app.services.vector_service.VectorService.get_embedding") as mock_emb, \
         mock.patch("app.services.vector_service.VectorService.get_all_documents") as mock_get_all, \
         mock.patch("pydantic_ai.Agent.run", new_callable=mock.AsyncMock) as mock_run:
        
        # Mock embeddings: return a list of 1536 zeros
        mock_emb_async.return_value = [0.0] * 1536
        mock_emb.return_value = [0.0] * 1536
        
        # Mock get_all_documents: return one fake chunk
        mock_get_all.return_value = [{
            "content": "Mock document content",
            "metadata": {"doc_name": "mock.txt", "page": "1"}
        }]
        
        async def sophisticated_side_effect(prompt, **kwargs):
            # We'll use the prompt content to guess which agent it is
            p = str(prompt).lower()
            if "extracting features from a document chunk" in p or "temp-001" in p:
                res = ChunkFeatures(
                    features=[FeatureDraft(
                        feature_id="TEMP-001", title="Mock Feature",
                        problem_statement="Problem", benefit="Benefit",
                        business_process="Process", scope="Scope", sources=["Source"]
                    )],
                    chunk_summary="Summary"
                )
            elif "consolidating features from multiple document chunks" in p or "f-001" in p:
                res = FeatureExtractionResult(
                    features=[FeatureDraft(
                        feature_id="F-001", title="Mock Feature",
                        problem_statement="Problem", benefit="Benefit",
                        business_process="Process", scope="Scope", sources=["Source"]
                    )],
                    summary="Overall Summary"
                )
            elif "discovery interview" in p or "q-001" in p:
                res = SingleFeatureInterviewResult(
                    questions=[InterviewQuestion(
                        question_id="Q-001", feature_id="F-001",
                        question="Mock Question?", question_type=QuestionType.scope,
                        suggested_answer="Suggested Answer"
                    )]
                )
            else: # Story generation
                res = Feature(
                    feature_id="F-001", title="Mock Feature",
                    problem_statement="Problem", benefit="Benefit",
                    business_process="Process", scope="Scope", sources=["Source"],
                    user_stories=[UserStory(
                        story_id="US-001", as_a="User", i_want="Feature",
                        so_that="Benefit",
                        acceptance_criteria=[AcceptanceCriterion(
                            given="Given", when="When", then="Then"
                        )]
                    )]
                )
            return mock.Mock(output=res)

        mock_run.side_effect = sophisticated_side_effect
        
        yield (mock_emb, mock_run)


@pytest.fixture(scope="module")
def tmp_data_dir():
    """Create an isolated temp directory for test data, cleaned up after."""
    d = tempfile.mkdtemp(prefix="ba_toolkit_test_")
    os.makedirs(os.path.join(d, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(d, "vectors"), exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def client(tmp_data_dir):
    """
    Create a TestClient with settings pointing to the temp directory.
    Resets the singleton DB so each test module gets a fresh database.
    """
    # Patch settings before importing app
    os.environ["DATABASE_PATH"] = os.path.join(tmp_data_dir, "app.db")
    os.environ["VECTOR_DB_PATH"] = os.path.join(tmp_data_dir, "vectors")
    os.environ["UPLOAD_DIR"] = os.path.join(tmp_data_dir, "uploads")
    
    # Set fake keys to pass HAS_OPENAI_KEY / HAS_AZURE_KEY checks
    os.environ["OPENAI_API_KEY"] = "mock_key"
    os.environ["AZURE_OPENAI_API_KEY"] = "mock_key"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock.openai.azure.com"

    # Reset the global DB singleton so it picks up new settings
    import app.auth.dependencies as deps
    deps._db = None

    # Reload settings
    from app.config import Settings
    fresh = Settings()
    import app.config
    app.config.settings = fresh

    from app.main import app
    with TestClient(app) as c:
        yield c

    # Cleanup singleton
    deps._db = None


@pytest.fixture(scope="module")
def auth_headers(client):
    """Register a test user and return auth headers."""
    r = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "Test1234",
        "display_name": "Test User",
    })
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Helpers to detect whether external services are available
# In tests, we force these to True since we mock the calls
HAS_OPENAI_KEY = True
HAS_AZURE_KEY = True

requires_openai = pytest.mark.skipif(
    not HAS_OPENAI_KEY, reason="OPENAI_API_KEY not configured"
)
requires_azure = pytest.mark.skipif(
    not HAS_AZURE_KEY, reason="AZURE_OPENAI_API_KEY not configured"
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_register_returns_tokens(self, client):
        r = client.post("/api/auth/register", json={
            "email": "auth_test@example.com",
            "password": "Pwd12345",
            "display_name": "Auth Tester",
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_duplicate_register_rejected(self, client, auth_headers):
        r = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "Test1234",
            "display_name": "Test User",
        })
        assert r.status_code == 400

    def test_login_success(self, client):
        r = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "Test1234",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self, client):
        r = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrong",
        })
        assert r.status_code == 401

    def test_me_with_token(self, client, auth_headers):
        r = client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["email"] == "test@example.com"

    def test_me_without_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_refresh_token(self, client):
        # Login to get a refresh token
        r = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "Test1234",
        })
        refresh = r.json()["refresh_token"]
        r2 = client.post("/api/auth/refresh", params={"refresh_token": refresh})
        assert r2.status_code == 200
        assert "access_token" in r2.json()

    def test_invalid_refresh_token(self, client):
        r = client.post("/api/auth/refresh", params={"refresh_token": "bad"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class TestProjects:
    def test_create_project(self, client, auth_headers):
        r = client.post("/api/projects", headers=auth_headers, json={
            "name": "Test Project",
            "description": "For testing",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Test Project"
        assert data["id"]

    def test_list_projects(self, client, auth_headers):
        r = client.get("/api/projects", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_project(self, client, auth_headers):
        # Create then get
        r = client.post("/api/projects", headers=auth_headers, json={
            "name": "Get Test", "description": "",
        })
        pid = r.json()["id"]
        r2 = client.get(f"/api/projects/{pid}", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["id"] == pid

    def test_get_nonexistent_project(self, client, auth_headers):
        r = client.get("/api/projects/nonexistent", headers=auth_headers)
        assert r.status_code == 404

    def test_delete_project(self, client, auth_headers):
        r = client.post("/api/projects", headers=auth_headers, json={
            "name": "To Delete", "description": "",
        })
        pid = r.json()["id"]
        r2 = client.delete(f"/api/projects/{pid}", headers=auth_headers)
        assert r2.status_code == 200
        # Verify it's gone
        r3 = client.get(f"/api/projects/{pid}", headers=auth_headers)
        assert r3.status_code == 404


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class TestDocuments:
    def _create_project(self, client, auth_headers):
        r = client.post("/api/projects", headers=auth_headers, json={
            "name": "Doc Test Project", "description": "",
        })
        return r.json()["id"]

    def test_list_documents_empty(self, client, auth_headers):
        pid = self._create_project(client, auth_headers)
        r = client.get(f"/api/documents/{pid}", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()["documents"]) == 0

    @requires_openai
    def test_upload_txt_document(self, client, auth_headers):
        pid = self._create_project(client, auth_headers)
        content = (
            "The system shall allow users to manage their profiles. "
            "Users can update their name, email and avatar. "
            "Password reset must be supported via email verification."
        )
        file = io.BytesIO(content.encode())
        r = client.post(
            f"/api/documents/upload/{pid}",
            headers=auth_headers,
            files={"files": ("requirements.txt", file, "text/plain")},
        )
        assert r.status_code == 200
        docs = r.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["status"] == "success"
        assert docs[0]["total_chunks"] > 0

    @requires_openai
    def test_delete_document(self, client, auth_headers):
        pid = self._create_project(client, auth_headers)
        content = b"Some test content for deletion test."
        r = client.post(
            f"/api/documents/upload/{pid}",
            headers=auth_headers,
            files={"files": ("del_test.txt", io.BytesIO(content), "text/plain")},
        )
        doc_id = r.json()["documents"][0]["doc_id"]
        r2 = client.delete(f"/api/documents/{doc_id}", headers=auth_headers)
        assert r2.status_code == 200


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class TestAnalysis:
    def _create_project(self, client, auth_headers):
        r = client.post("/api/projects", headers=auth_headers, json={
            "name": "Analysis Test", "description": "",
        })
        return r.json()["id"]

    def test_status_no_session(self, client, auth_headers):
        pid = self._create_project(client, auth_headers)
        r = client.get(f"/api/analysis/{pid}/status", headers=auth_headers)
        assert r.status_code == 404

    def test_start_analysis_no_documents(self, client, auth_headers):
        pid = self._create_project(client, auth_headers)
        r = client.post(
            f"/api/analysis/{pid}/start",
            headers=auth_headers,
            json={"mode": "auto"},
        )
        assert r.status_code == 400
        assert "No documents" in r.json()["detail"]

    @requires_openai
    @requires_azure
    def test_start_analysis_with_document(self, client, auth_headers):
        """Full pipeline test — only runs when both API keys are present."""
        import time

        pid = self._create_project(client, auth_headers)

        # Upload a document first
        content = (
            "The system shall allow users to manage profiles. "
            "Admin dashboard shows analytics. "
            "Reporting module generates PDF reports."
        )
        client.post(
            f"/api/documents/upload/{pid}",
            headers=auth_headers,
            files={"files": ("spec.txt", io.BytesIO(content.encode()), "text/plain")},
        )

        # Start analysis
        r = client.post(
            f"/api/analysis/{pid}/start",
            headers=auth_headers,
            json={"mode": "auto"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"]
        assert data["status"] == "extracting"

        # Poll until done or error (max 120s)
        for _ in range(40):
            time.sleep(3)
            r = client.get(f"/api/analysis/{pid}/status", headers=auth_headers)
            status = r.json()["status"]
            if status in ("done", "error"):
                break

        assert status == "done", f"Analysis ended with status: {status}"

    def test_export_no_analysis(self, client, auth_headers):
        pid = self._create_project(client, auth_headers)
        r = client.get(f"/api/analysis/{pid}/export", headers=auth_headers)
        # 404 because no session, or 400 because not done
        assert r.status_code in (400, 404)

    def test_list_sessions_empty(self, client, auth_headers):
        pid = self._create_project(client, auth_headers)
        r = client.get(f"/api/analysis/{pid}/sessions", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_list_sessions_after_analysis(self, client, auth_headers):
        """Run analysis, then verify session appears in history."""
        import time

        pid = self._create_project(client, auth_headers)

        # Upload doc
        client.post(
            f"/api/documents/upload/{pid}",
            headers=auth_headers,
            files={"files": ("test.txt", io.BytesIO(b"Test content"), "text/plain")},
        )

        # Start analysis
        r = client.post(
            f"/api/analysis/{pid}/start", headers=auth_headers,
            json={"mode": "auto"},
        )
        session_id = r.json()["session_id"]

        # Wait for completion
        for _ in range(20):
            time.sleep(0.5)
            r = client.get(f"/api/analysis/{pid}/status", headers=auth_headers)
            if r.json()["status"] in ("done", "error"):
                break

        # List sessions
        r = client.get(f"/api/analysis/{pid}/sessions", headers=auth_headers)
        assert r.status_code == 200
        sessions = r.json()
        assert len(sessions) >= 1
        assert sessions[0]["session_id"] == session_id
        assert "created_at" in sessions[0]

    def test_get_historical_session(self, client, auth_headers):
        """Run analysis twice, verify both sessions accessible."""
        import time

        pid = self._create_project(client, auth_headers)
        client.post(
            f"/api/documents/upload/{pid}",
            headers=auth_headers,
            files={"files": ("test.txt", io.BytesIO(b"Test content"), "text/plain")},
        )

        # Run first analysis
        r1 = client.post(
            f"/api/analysis/{pid}/start", headers=auth_headers,
            json={"mode": "auto"},
        )
        sid1 = r1.json()["session_id"]
        for _ in range(20):
            time.sleep(0.5)
            r = client.get(f"/api/analysis/{pid}/status", headers=auth_headers)
            if r.json()["status"] in ("done", "error"):
                break

        # Run second analysis
        r2 = client.post(
            f"/api/analysis/{pid}/start", headers=auth_headers,
            json={"mode": "auto"},
        )
        sid2 = r2.json()["session_id"]
        for _ in range(20):
            time.sleep(0.5)
            r = client.get(f"/api/analysis/{pid}/status", headers=auth_headers)
            if r.json()["status"] in ("done", "error"):
                break

        # /status returns latest (sid2)
        r = client.get(f"/api/analysis/{pid}/status", headers=auth_headers)
        assert r.json()["session_id"] == sid2

        # But old session is still accessible via /sessions/{session_id}
        r = client.get(f"/api/analysis/{pid}/sessions/{sid1}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["session_id"] == sid1

        # Sessions list has both
        r = client.get(f"/api/analysis/{pid}/sessions", headers=auth_headers)
        ids = [s["session_id"] for s in r.json()]
        assert sid1 in ids
        assert sid2 in ids

    def test_delete_document_cleans_disk(self, client, auth_headers, tmp_data_dir):
        """Verify physical file is removed after document deletion."""
        pid = self._create_project(client, auth_headers)
        content = b"Content for disk cleanup test."
        r = client.post(
            f"/api/documents/upload/{pid}",
            headers=auth_headers,
            files={"files": ("cleanup.txt", io.BytesIO(content), "text/plain")},
        )
        doc_id = r.json()["documents"][0]["doc_id"]

        # Verify file exists on disk
        upload_dir = os.path.join(tmp_data_dir, "uploads")
        files_before = os.listdir(upload_dir)
        matching = [f for f in files_before if doc_id in f]
        assert len(matching) == 1, f"Expected file on disk, found: {files_before}"

        # Delete document
        r = client.delete(f"/api/documents/{doc_id}", headers=auth_headers)
        assert r.status_code == 200

        # Verify file is gone
        files_after = os.listdir(upload_dir)
        matching_after = [f for f in files_after if doc_id in f]
        assert len(matching_after) == 0, f"File not cleaned up: {files_after}"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["name"] == "BA Toolkit API"

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
