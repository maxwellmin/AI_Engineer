from django.apps import AppConfig


class DocumentRagSearchConfig(AppConfig):
    """Django app configuration for document RAG search module.

    This module provides hybrid search functionality combining:
    - Vector search (Milvus)
    - Keyword search (PostgreSQL FTS)
    - Graph search (Neo4j)

    Results are fused using RRF (Reciprocal Rank Fusion) ranking.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.document_rag_search"
    verbose_name = "Document RAG Search"
