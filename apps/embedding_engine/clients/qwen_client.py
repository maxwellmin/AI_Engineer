"""
Qwen embedding client implementation.

This module provides the QwenEmbeddingClient for generating embeddings
using the Qwen API (dashscope).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from apps.embedding_engine.constants import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_BATCH_SIZE,
    DEFAULT_DIMENSION,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT,
    QWEN_API_BASE_URL,
    QWEN_EMBEDDING_API_PATH,
    TaskType,
)
from apps.embedding_engine.dto import BatchEmbeddingResult, EmbeddingResult
from apps.embedding_engine.exceptions import (
    EmbeddingAPIError,
    EmbeddingBatchSizeError,
    EmbeddingConnectionError,
    EmbeddingEmptyInputError,
    EmbeddingInputTooLongError,
    EmbeddingInvalidResponseError,
    EmbeddingRateLimitError,
    EmbeddingTimeoutError,
    MissingAPIKeyError,
)

logger = logging.getLogger(__name__)


class QwenEmbeddingClient:
    """Client for Qwen embedding API.

    This client interacts with the Qwen (dashscope) embedding API to generate
    dense vector embeddings for text.

    Attributes:
        api_key: API key for authentication.
        base_url: Base URL for the API.
        model: Default embedding model.
        dimension: Embedding dimension.

    Example:
        >>> client = QwenEmbeddingClient(api_key="sk-xxx")
        >>> result = client.embed_single("Hello world")
        >>> print(result.embedding[:5])
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        backoff_factor: float | None = None,
    ) -> None:
        """Initialize the Qwen embedding client.

        Args:
            api_key: API key for authentication. Required.
            base_url: Base URL for the API.
            model: Default embedding model.
            dimension: Embedding dimension.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries.
            backoff_factor: Backoff factor for retry delays.
        """
        if not api_key:
            raise MissingAPIKeyError()

        self._api_key = api_key
        self._base_url = base_url or QWEN_API_BASE_URL
        self._model = model or DEFAULT_MODEL
        self._dimension = dimension or DEFAULT_DIMENSION
        self._timeout = timeout or DEFAULT_TIMEOUT
        self._max_retries = max_retries or DEFAULT_MAX_RETRIES
        self._backoff_factor = backoff_factor or DEFAULT_BACKOFF_FACTOR

        # HTTP client (trust_env=False to ignore system proxy settings)
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            trust_env=False,  # Ignore system proxy settings, use direct connection
        )

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension

    @property
    def model(self) -> str:
        """Return the default model name."""
        return self._model

    def _build_request_body(
        self,
        texts: list[str],
        model: str | None = None,
        task_type: str | None = None,
    ) -> dict[str, Any]:
        """Build the request body for the API.

        Args:
            texts: List of texts to embed.
            model: Model to use.
            task_type: Task type for embedding.

        Returns:
            Request body dictionary.
        """
        body: dict[str, Any] = {
            "model": model or self._model,
            "input": texts,
        }

        # Add task_type if specified (Qwen API specific)
        if task_type:
            body["parameters"] = {"task_type": task_type}

        return body

    def _parse_response(
        self,
        response: httpx.Response,
        texts_count: int,
    ) -> BatchEmbeddingResult:
        """Parse the API response.

        Args:
            response: HTTP response.
            texts_count: Expected number of embeddings.

        Returns:
            BatchEmbeddingResult with embeddings.

        Raises:
            EmbeddingAPIError: If API returns an error.
            EmbeddingInvalidResponseError: If response format is invalid.
        """
        # Check for HTTP errors
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise EmbeddingRateLimitError(
                retry_after=float(retry_after) if retry_after else None
            )

        if response.status_code == 401:
            raise EmbeddingAPIError("Invalid API key", status_code=401)

        if response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get("message", "Bad request")
            if "token" in error_msg.lower():
                raise EmbeddingInputTooLongError(
                    token_count=0, max_tokens=0  # Unknown token count
                )
            raise EmbeddingAPIError(error_msg, status_code=400)

        if response.status_code >= 500:
            raise EmbeddingAPIError(
                f"API server error: {response.status_code}",
                status_code=response.status_code,
            )

        if response.status_code != 200:
            raise EmbeddingAPIError(
                f"API request failed: {response.status_code}",
                status_code=response.status_code,
            )

        # Parse response
        try:
            data = response.json()
        except Exception as e:
            raise EmbeddingInvalidResponseError(f"Failed to parse JSON: {e}")

        # Validate response structure
        if "data" not in data:
            raise EmbeddingInvalidResponseError("Missing 'data' field in response")

        embeddings_data = data.get("data", [])
        if not isinstance(embeddings_data, list):
            raise EmbeddingInvalidResponseError("'data' is not a list")

        if len(embeddings_data) != texts_count:
            raise EmbeddingInvalidResponseError(
                f"Expected {texts_count} embeddings, got {len(embeddings_data)}"
            )

        # Extract embeddings (sorted by index)
        embeddings_data = sorted(embeddings_data, key=lambda x: x.get("index", 0))
        embeddings = [item.get("embedding", []) for item in embeddings_data]

        # Validate dimensions
        for i, emb in enumerate(embeddings):
            if len(emb) != self._dimension:
                raise EmbeddingInvalidResponseError(
                    f"Embedding {i} has wrong dimension: "
                    f"expected {self._dimension}, got {len(emb)}"
                )

        # Extract usage
        usage = data.get("usage", {})
        total_tokens = usage.get("total_tokens", 0)

        return BatchEmbeddingResult(
            embeddings=embeddings,
            dimension=self._dimension,
            model=self._model,
            total_tokens=total_tokens,
            success_count=len(embeddings),
        )

    @retry(
        retry=retry_if_exception_type(EmbeddingConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True,
    )
    def _make_request(
        self,
        body: dict[str, Any],
        texts_count: int,
    ) -> BatchEmbeddingResult:
        """Make the API request with retry logic.

        Args:
            body: Request body.
            texts_count: Expected number of embeddings.

        Returns:
            BatchEmbeddingResult with embeddings.
        """
        try:
            response = self._client.post(
                QWEN_EMBEDDING_API_PATH,
                json=body,
            )
            return self._parse_response(response, texts_count)
        except httpx.TimeoutException as e:
            raise EmbeddingTimeoutError(timeout=self._timeout)
        except httpx.ConnectError as e:
            raise EmbeddingConnectionError(str(e))
        except EmbeddingRateLimitError:
            # Don't retry rate limit errors
            raise
        except EmbeddingAPIError:
            # Don't retry API errors
            raise
        except Exception as e:
            logger.exception("Unexpected error during embedding request")
            raise EmbeddingAPIError(f"Unexpected error: {e}")

    def embed(
        self,
        texts: list[str],
        model: str | None = None,
        **kwargs: Any,
    ) -> BatchEmbeddingResult:
        """Embed a list of texts.

        Args:
            texts: List of text strings to embed.
            model: Optional model override.
            **kwargs: Additional parameters.
                - task_type: Task type for embedding.

        Returns:
            BatchEmbeddingResult with embeddings.

        Raises:
            EmbeddingEmptyInputError: If texts list is empty.
            EmbeddingAPIError: If API request fails.
        """
        if not texts:
            raise EmbeddingEmptyInputError()

        # Filter empty strings
        non_empty_texts = [t for t in texts if t.strip()]
        if not non_empty_texts:
            raise EmbeddingEmptyInputError()

        task_type = kwargs.get("task_type")

        # Build request
        body = self._build_request_body(
            texts=non_empty_texts,
            model=model,
            task_type=task_type,
        )

        # Make request
        return self._make_request(body, len(non_empty_texts))

    def embed_single(
        self,
        text: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        """Embed a single text.

        Args:
            text: Text string to embed.
            model: Optional model override.
            **kwargs: Additional parameters.
                - task_type: Task type for embedding.

        Returns:
            EmbeddingResult with embedding.

        Raises:
            EmbeddingEmptyInputError: If text is empty.
            EmbeddingAPIError: If API request fails.
        """
        if not text or not text.strip():
            raise EmbeddingEmptyInputError()

        # Use embed() for single text
        batch_result = self.embed([text], model=model, **kwargs)

        return EmbeddingResult(
            embedding=batch_result.embeddings[0],
            dimension=batch_result.dimension,
            model=batch_result.model,
            tokens_used=batch_result.total_tokens,
        )

    def health_check(self) -> bool:
        """Check if the embedding service is healthy.

        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            # Try to embed a simple test text
            result = self.embed_single("health check", model=self._model)
            return len(result.embedding) == self._dimension
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "QwenEmbeddingClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def __del__(self) -> None:
        """Destructor to ensure client is closed."""
        try:
            self.close()
        except Exception:
            pass
