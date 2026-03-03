"""
DRF serializers for embedding engine API.

This module defines serializers for the embedding engine HTTP API endpoints.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.embedding_engine.constants import MAX_TOKENS_PER_REQUEST


# =============================================================================
# Request Serializers
# =============================================================================


class EmbedRequestSerializer(serializers.Serializer):
    """Serializer for single text embedding request.

    Attributes:
        text: Text content to embed.
        task_type: Task type (document or query).
    """

    text = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=100000,  # High limit, actual token validation in validate_text()
        help_text="Text content to embed",
    )
    task_type = serializers.ChoiceField(
        choices=["retrieval.document", "retrieval.query"],
        default="retrieval.document",
        help_text="Task type: 'retrieval.document' for documents, 'retrieval.query' for queries",
    )

    def validate_text(self, value: str) -> str:
        """Validate text length based on estimated token count.

        Args:
            value: Text to validate.

        Returns:
            Validated text.

        Raises:
            ValidationError: If text exceeds token limit.
        """
        # Rough token estimation: ~4 chars per token for English, ~2 for Chinese
        # Use conservative estimate of 3 chars per token
        estimated_tokens = len(value) // 3
        if estimated_tokens > MAX_TOKENS_PER_REQUEST:
            raise serializers.ValidationError(
                f"Text too long: estimated {estimated_tokens} tokens "
                f"(max: {MAX_TOKENS_PER_REQUEST}). "
                f"Please reduce text length."
            )
        return value


class EmbedBatchRequestSerializer(serializers.Serializer):
    """Serializer for batch text embedding request.

    Attributes:
        texts: List of texts to embed.
        task_type: Task type (document or query).
        batch_size: Number of texts per API call.
    """

    texts = serializers.ListField(
        child=serializers.CharField(max_length=100000),  # High limit, actual token validation in validate_texts()
        required=True,
        allow_empty=False,
        max_length=100,  # Max 100 texts per batch
        help_text="List of text contents to embed",
    )
    task_type = serializers.ChoiceField(
        choices=["retrieval.document", "retrieval.query"],
        default="retrieval.document",
        help_text="Task type: 'retrieval.document' for documents, 'retrieval.query' for queries",
    )
    batch_size = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=50,
        help_text="Number of texts per API call",
    )

    def validate_texts(self, value: list[str]) -> list[str]:
        """Validate each text length based on estimated token count.

        Args:
            value: List of texts to validate.

        Returns:
            Validated texts.

        Raises:
            ValidationError: If any text exceeds token limit.
        """
        for i, text in enumerate(value):
            estimated_tokens = len(text) // 3
            if estimated_tokens > MAX_TOKENS_PER_REQUEST:
                raise serializers.ValidationError(
                    f"Text at index {i} too long: estimated {estimated_tokens} tokens "
                    f"(max: {MAX_TOKENS_PER_REQUEST}). "
                    f"Please reduce text length."
                )
        return value


class EmbedQueryRequestSerializer(serializers.Serializer):
    """Serializer for query embedding request.

    Attributes:
        query: Query text to embed.
    """

    query = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=10000,  # ~2.5k tokens max for queries
        help_text="Query text to embed for search",
    )


# =============================================================================
# Response Serializers
# =============================================================================


class EmbeddingResultSerializer(serializers.Serializer):
    """Serializer for single embedding result.

    Attributes:
        embedding: Dense vector.
        dimension: Vector dimension.
        model: Model used for embedding.
        tokens_used: Number of tokens consumed.
    """

    embedding = serializers.ListField(
        child=serializers.FloatField(),
        help_text="Dense vector embedding",
    )
    dimension = serializers.IntegerField(
        help_text="Vector dimension",
    )
    model = serializers.CharField(
        help_text="Model used for embedding",
    )
    tokens_used = serializers.IntegerField(
        help_text="Number of tokens consumed",
    )


class BatchEmbeddingResultSerializer(serializers.Serializer):
    """Serializer for batch embedding result.

    Attributes:
        embeddings: List of dense vectors.
        dimension: Vector dimension.
        model: Model used for embedding.
        total_tokens: Total tokens consumed.
        success_count: Number of successful embeddings.
        failed_count: Number of failed embeddings.
    """

    embeddings = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        help_text="List of dense vector embeddings",
    )
    dimension = serializers.IntegerField(
        help_text="Vector dimension",
    )
    model = serializers.CharField(
        help_text="Model used for embedding",
    )
    total_tokens = serializers.IntegerField(
        help_text="Total tokens consumed",
    )
    success_count = serializers.IntegerField(
        help_text="Number of successful embeddings",
    )
    failed_count = serializers.IntegerField(
        default=0,
        help_text="Number of failed embeddings",
    )


class HealthCheckSerializer(serializers.Serializer):
    """Serializer for health check response.

    Attributes:
        healthy: Whether the service is healthy.
        provider: Provider type (qwen or mock).
        model: Model name.
        dimension: Embedding dimension.
        latency_ms: Response latency in milliseconds.
        error: Error message if unhealthy.
    """

    healthy = serializers.BooleanField(
        help_text="Whether the service is healthy",
    )
    provider = serializers.CharField(
        help_text="Provider type (qwen or mock)",
    )
    model = serializers.CharField(
        help_text="Model name",
    )
    dimension = serializers.IntegerField(
        help_text="Embedding dimension",
    )
    latency_ms = serializers.FloatField(
        help_text="Response latency in milliseconds",
    )
    error = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="Error message if unhealthy",
    )


class SupportedModelsSerializer(serializers.Serializer):
    """Serializer for supported models response.

    Attributes:
        models: List of supported model names.
    """

    models = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of supported embedding model names",
    )


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error response.

    Attributes:
        error: Error type.
        message: Error message.
        detail: Additional error details.
    """

    error = serializers.CharField(
        help_text="Error type",
    )
    message = serializers.CharField(
        help_text="Error message",
    )
    detail = serializers.DictField(
        required=False,
        help_text="Additional error details",
    )
