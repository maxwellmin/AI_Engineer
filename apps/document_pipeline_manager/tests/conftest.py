"""
Pytest fixtures for Document Pipeline Manager tests.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.documents_parser.models import Document
from apps.document_pipeline_manager.models import PipelineExecution, PipelineStep


# =============================================================================
# User Fixtures
# =============================================================================


@pytest.fixture
def test_user(db):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def another_user(db):
    """Create another test user."""
    User = get_user_model()
    return User.objects.create_user(
        username="anotheruser",
        email="another@example.com",
        password="testpass456",
    )


# =============================================================================
# Document Fixtures
# =============================================================================


@pytest.fixture
def test_document(db, test_user):
    """Create a test document."""
    return Document.objects.create(
        user=test_user,
        name="test_document.pdf",
        original_name="Test Document.pdf",
        file_path="documents/test/test_document.pdf",
        file_size=1024000,
        file_type="pdf",
        file_hash="abc123def456",
        status=Document.Status.UPLOADED,
    )


@pytest.fixture
def test_document_processing(db, test_user):
    """Create a test document with processing status."""
    return Document.objects.create(
        user=test_user,
        name="processing_document.pdf",
        original_name="Processing Document.pdf",
        file_path="documents/test/processing_document.pdf",
        file_size=512000,
        file_type="pdf",
        file_hash="processing123hash",
        status=Document.Status.PROCESSING,
    )


@pytest.fixture
def test_document_done(db, test_user):
    """Create a test document with done status."""
    return Document.objects.create(
        user=test_user,
        name="done_document.pdf",
        original_name="Done Document.pdf",
        file_path="documents/test/done_document.pdf",
        file_size=2048000,
        file_type="pdf",
        file_hash="done123hash",
        status=Document.Status.DONE,
    )


@pytest.fixture
def test_document_txt(db, test_user):
    """Create a test TXT document."""
    return Document.objects.create(
        user=test_user,
        name="test_document.txt",
        original_name="Test Document.txt",
        file_path="documents/test/test_document.txt",
        file_size=5000,
        file_type="txt",
        file_hash="txt123hash",
        status=Document.Status.UPLOADED,
    )


# =============================================================================
# Pipeline Execution Fixtures
# =============================================================================


@pytest.fixture
def test_execution(db, test_document):
    """Create a test pipeline execution in pending state."""
    return PipelineExecution.objects.create(
        document=test_document,
        status=PipelineExecution.Status.PENDING,
    )


@pytest.fixture
def test_execution_running(db, test_document):
    """Create a test pipeline execution in running state."""
    from django.utils import timezone

    execution = PipelineExecution.objects.create(
        document=test_document,
        status=PipelineExecution.Status.RUNNING,
        started_at=timezone.now(),
        current_step="embed",
    )

    # Create step records
    steps_data = [
        ("parse", 1, PipelineStep.Status.COMPLETED, 1500),
        ("chunk", 2, PipelineStep.Status.COMPLETED, 800),
        ("embed", 3, PipelineStep.Status.RUNNING, 0),
        ("vectorize", 4, PipelineStep.Status.PENDING, 0),
        ("graph", 5, PipelineStep.Status.PENDING, 0),
        ("extract", 6, PipelineStep.Status.PENDING, 0),
    ]

    for step_name, step_order, status, duration in steps_data:
        PipelineStep.objects.create(
            execution=execution,
            step_name=step_name,
            step_order=step_order,
            status=status,
            duration_ms=duration,
        )

    return execution


@pytest.fixture
def test_execution_completed(db, test_document_done):
    """Create a test pipeline execution in completed state."""
    from django.utils import timezone

    now = timezone.now()

    execution = PipelineExecution.objects.create(
        document=test_document_done,
        status=PipelineExecution.Status.COMPLETED,
        started_at=now,
        completed_at=now,
        total_duration_ms=5000,
        current_step="extract",
    )

    # Create completed step records
    steps_data = [
        ("parse", 1, 1500, {"text_length": 5000, "page_count": 10}),
        ("chunk", 2, 800, {"chunk_count": 15}),
        ("embed", 3, 1200, {"embedded_count": 15}),
        ("vectorize", 4, 500, {"vectorized_count": 15}),
        ("graph", 5, 600, {"chunks_created": 15}),
        ("extract", 6, 400, {"entities_extracted": 5}),
    ]

    for step_name, step_order, duration, output in steps_data:
        PipelineStep.objects.create(
            execution=execution,
            step_name=step_name,
            step_order=step_order,
            status=PipelineStep.Status.COMPLETED,
            duration_ms=duration,
            output_data=output,
        )

    return execution


@pytest.fixture
def test_execution_failed(db, test_document):
    """Create a test pipeline execution in failed state."""
    from django.utils import timezone

    now = timezone.now()

    execution = PipelineExecution.objects.create(
        document=test_document,
        status=PipelineExecution.Status.FAILED,
        started_at=now,
        completed_at=now,
        total_duration_ms=2000,
        current_step="embed",
        error_step="embed",
        error_message="Embedding generation failed: API timeout",
        retry_count=2,
    )

    # Create step records with one failure
    steps_data = [
        ("parse", 1, PipelineStep.Status.COMPLETED, 1500),
        ("chunk", 2, PipelineStep.Status.COMPLETED, 800),
        ("embed", 3, PipelineStep.Status.FAILED, 200),
        ("vectorize", 4, PipelineStep.Status.SKIPPED, 0),
        ("graph", 5, PipelineStep.Status.SKIPPED, 0),
        ("extract", 6, PipelineStep.Status.SKIPPED, 0),
    ]

    for step_name, step_order, status, duration in steps_data:
        error_msg = "Embedding generation failed: API timeout" if status == PipelineStep.Status.FAILED else ""
        PipelineStep.objects.create(
            execution=execution,
            step_name=step_name,
            step_order=step_order,
            status=status,
            duration_ms=duration,
            error_message=error_msg,
        )

    return execution


@pytest.fixture
def test_execution_cancelled(db, test_document):
    """Create a test pipeline execution in cancelled state."""
    from django.utils import timezone

    now = timezone.now()

    execution = PipelineExecution.objects.create(
        document=test_document,
        status=PipelineExecution.Status.CANCELLED,
        started_at=now,
        completed_at=now,
        total_duration_ms=1000,
        current_step="chunk",
    )

    # Create step records
    steps_data = [
        ("parse", 1, PipelineStep.Status.COMPLETED, 1500),
        ("chunk", 2, PipelineStep.Status.SKIPPED, 0),
        ("embed", 3, PipelineStep.Status.SKIPPED, 0),
        ("vectorize", 4, PipelineStep.Status.SKIPPED, 0),
        ("graph", 5, PipelineStep.Status.SKIPPED, 0),
        ("extract", 6, PipelineStep.Status.SKIPPED, 0),
    ]

    for step_name, step_order, status, duration in steps_data:
        PipelineStep.objects.create(
            execution=execution,
            step_name=step_name,
            step_order=step_order,
            status=status,
            duration_ms=duration,
        )

    return execution


# =============================================================================
# Service Fixtures
# =============================================================================


@pytest.fixture
def pipeline_service():
    """Create a PipelineService instance."""
    from apps.document_pipeline_manager.services import PipelineService
    from apps.document_pipeline_manager.dto import PipelineConfig

    config = PipelineConfig(
        max_retries=3,
        batch_size=20,
        enable_entity_extraction=True,
    )
    return PipelineService(config)


@pytest.fixture
def pipeline_orchestrator():
    """Create a PipelineOrchestrator instance."""
    from apps.document_pipeline_manager.orchestrator import PipelineOrchestrator
    from apps.document_pipeline_manager.dto import PipelineConfig

    config = PipelineConfig(
        max_retries=3,
        batch_size=20,
        enable_entity_extraction=True,
    )
    return PipelineOrchestrator(config)


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_file_content():
    """Return mock file content for testing."""
    return b"This is a test document content for pipeline processing.\n" * 100


@pytest.fixture
def mock_parsed_document():
    """Return mock parsed document data."""
    return {
        "content": "This is the parsed content of the document. " * 50,
        "page_count": 5,
        "metadata": {
            "title": "Test Document",
            "author": "Test Author",
        },
    }


@pytest.fixture
def mock_chunks():
    """Return mock chunk data for testing."""
    return [
        {
            "id": "chunk-1",
            "content": "This is the first chunk of content.",
            "index": 0,
        },
        {
            "id": "chunk-2",
            "content": "This is the second chunk of content.",
            "index": 1,
        },
        {
            "id": "chunk-3",
            "content": "This is the third chunk of content.",
            "index": 2,
        },
    ]


@pytest.fixture
def mock_embeddings():
    """Return mock embedding vectors."""
    import random

    dimension = 1536
    return [random.uniform(-1, 1) for _ in range(dimension)]
