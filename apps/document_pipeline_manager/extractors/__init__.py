"""
Entity Extractors for Document Pipeline Manager.

This module provides entity extraction capabilities for the pipeline.
"""

from apps.document_pipeline_manager.extractors.base import BaseEntityExtractor
from apps.document_pipeline_manager.extractors.mock_extractor import MockEntityExtractor

__all__ = [
    "BaseEntityExtractor",
    "MockEntityExtractor",
]
