"""
Services module for Milvus database controller.

This module contains high-level service classes that coordinate
multiple managers to provide unified business logic.
"""

from apps.milvus_database_controller.services.milvus_service import MilvusService

__all__ = ["MilvusService"]
