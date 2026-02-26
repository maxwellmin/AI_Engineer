"""
Milvus client module.

This module provides the MilvusClient singleton wrapper for connection management.
"""

from apps.milvus_database_controller.client.milvus_client import MilvusClientWrapper

__all__ = ["MilvusClientWrapper"]
