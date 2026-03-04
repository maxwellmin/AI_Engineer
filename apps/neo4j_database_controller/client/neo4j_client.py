"""
Neo4j client wrapper with connection management.

This module provides a singleton Neo4jClient wrapper that manages connections
to the Neo4j server and provides a thread-safe interface for all Neo4j operations.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Generator

from django.conf import settings
from neo4j import GraphDatabase
from neo4j import exceptions as neo4j_exceptions
from neo4j.graph import Node, Relationship

from apps.neo4j_database_controller.constants import (
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_MAX_CONNECTION_POOL_SIZE,
    DEFAULT_MAX_TRANSACTION_RETRY_TIME,
    DEFAULT_QUERY_TIMEOUT,
    SessionMode,
)
from apps.neo4j_database_controller.exceptions import (
    ConfigurationError,
    MissingConfigurationError,
    Neo4jAuthError,
    Neo4jConnectionError,
    Neo4jConnectionTimeoutError,
    QueryError,
    TransactionError,
)

if TYPE_CHECKING:
    from neo4j import Driver, Session

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Singleton wrapper for Neo4j driver with connection management.

    This class provides:
    - Singleton pattern for connection reuse
    - Thread-safe driver access
    - Automatic reconnection on failure
    - Configuration from Django settings
    - Session and transaction management

    Example:
        >>> client = Neo4jClient.get_instance()
        >>> with client.session() as session:
        ...     result = session.run("MATCH (n) RETURN n LIMIT 1")
    """

    _instance: Neo4jClient | None = None
    _lock: threading.Lock = threading.Lock()
    _driver: Driver | None = None

    def __new__(cls) -> Neo4jClient:
        """Create or return the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the Neo4jClient wrapper."""
        # Only initialize once
        if not hasattr(self, "_initialized"):
            self._initialized = False
            self._config = self._load_config()
            self._initialized = True

    @classmethod
    def get_instance(cls) -> Neo4jClient:
        """Get the singleton instance of Neo4jClient.

        Returns:
            The singleton Neo4jClient instance.
        """
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance.

        This is useful for testing or when reconnecting with new configuration.
        """
        with cls._lock:
            if cls._instance is not None:
                try:
                    if cls._instance._driver is not None:
                        cls._instance._driver.close()
                except Exception as e:
                    logger.warning(f"Error closing Neo4j driver: {e}")
                finally:
                    cls._instance._driver = None
            cls._instance = None

    def _load_config(self) -> dict[str, Any]:
        """Load Neo4j configuration from Django settings.

        Returns:
            Dictionary containing Neo4j configuration.

        Raises:
            MissingConfigurationError: If required configuration is missing.
        """
        neo4j_config = getattr(settings, "NEO4J_CONFIG", {})

        # Get required connection settings
        uri = neo4j_config.get("uri") or getattr(settings, "NEO4J_URI", None)
        user = neo4j_config.get("user") or getattr(settings, "NEO4J_USER", None)
        password = neo4j_config.get("password") or getattr(settings, "NEO4J_PASSWORD", None)

        if not uri:
            raise MissingConfigurationError("NEO4J_URI")
        if not user:
            raise MissingConfigurationError("NEO4J_USER")

        # Password can be empty for some auth methods, but warn
        if not password:
            logger.warning("NEO4J_PASSWORD is not set. This may cause authentication errors.")

        config = {
            "uri": uri,
            "user": user,
            "password": password or "",
            "database": neo4j_config.get("database", "neo4j"),
            # Connection pool settings
            "max_connection_pool_size": neo4j_config.get(
                "max_connection_pool_size", DEFAULT_MAX_CONNECTION_POOL_SIZE
            ),
            "connection_timeout": neo4j_config.get(
                "connection_timeout", DEFAULT_CONNECTION_TIMEOUT
            ),
            "max_transaction_retry_time": neo4j_config.get(
                "max_transaction_retry_time", DEFAULT_MAX_TRANSACTION_RETRY_TIME
            ),
            # Query settings
            "default_query_timeout": neo4j_config.get(
                "default_query_timeout", DEFAULT_QUERY_TIMEOUT
            ),
        }

        logger.debug(f"Loaded Neo4j configuration: uri={uri}, database={config['database']}")
        return config

    def _get_driver(self) -> Driver:
        """Get or create the underlying Neo4j driver.

        Returns:
            Neo4j Driver instance.

        Raises:
            Neo4jConnectionError: If connection fails.
        """
        if self._driver is None:
            with self._lock:
                if self._driver is None:
                    self._connect()
        return self._driver

    def _connect(self) -> None:
        """Establish connection to Neo4j server.

        Raises:
            Neo4jConnectionError: If connection fails.
            Neo4jConnectionTimeoutError: If connection times out.
            Neo4jAuthError: If authentication fails.
        """
        try:
            logger.info(f"Connecting to Neo4j server at {self._config['uri']}")
            self._driver = GraphDatabase.driver(
                self._config["uri"],
                auth=(self._config["user"], self._config["password"]),
                max_connection_pool_size=self._config["max_connection_pool_size"],
                connection_timeout=self._config["connection_timeout"],
                max_transaction_retry_time=self._config["max_transaction_retry_time"],
            )
            # Verify connection
            self._driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j server")
        except neo4j_exceptions.AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise Neo4jAuthError(reason=str(e))
        except neo4j_exceptions.ServiceUnavailable as e:
            error_msg = str(e)
            logger.error(f"Neo4j service unavailable: {error_msg}")
            if "timeout" in error_msg.lower():
                raise Neo4jConnectionTimeoutError(
                    timeout=self._config["connection_timeout"]
                )
            raise Neo4jConnectionError(reason=error_msg)
        except neo4j_exceptions.ConfigurationError as e:
            logger.error(f"Neo4j configuration error: {e}")
            raise ConfigurationError("NEO4J_URI", reason=str(e))
        except Exception as e:
            logger.error(f"Unexpected error connecting to Neo4j: {e}")
            raise Neo4jConnectionError(reason=str(e))

    def _ensure_connected(self) -> None:
        """Ensure connection to Neo4j server.

        Raises:
            Neo4jConnectionError: If connection fails.
        """
        self._get_driver()

    def reconnect(self) -> bool:
        """Reconnect to Neo4j server.

        Returns:
            True if reconnection successful, False otherwise.
        """
        logger.info("Attempting to reconnect to Neo4j server")
        self.close()
        try:
            self._connect()
            return True
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return False

    def close(self) -> None:
        """Close the connection to Neo4j server."""
        if self._driver is not None:
            try:
                self._driver.close()
                logger.info("Closed connection to Neo4j server")
            except Exception as e:
                logger.warning(f"Error closing Neo4j connection: {e}")
            finally:
                self._driver = None

    # =========================================================================
    # Session Management
    # =========================================================================

    def session(
        self,
        mode: str = SessionMode.WRITE.value,
        database: str | None = None,
        **kwargs: Any,
    ) -> Session:
        """Create a new session.

        Args:
            mode: Session mode ("WRITE" or "READ").
            database: Database name (uses config default if not specified).
            **kwargs: Additional session parameters.

        Returns:
            Neo4j Session instance.
        """
        self._ensure_connected()

        access_mode = (
            "WRITE" if mode.upper() == SessionMode.WRITE.value else "READ"
        )

        return self._get_driver().session(
            database=database or self._config["database"],
            default_access_mode=access_mode,
            **kwargs,
        )

    def read_session(
        self,
        database: str | None = None,
        **kwargs: Any,
    ) -> Session:
        """Create a read-only session.

        Args:
            database: Database name.
            **kwargs: Additional session parameters.

        Returns:
            Neo4j Session instance in READ mode.
        """
        return self.session(mode=SessionMode.READ.value, database=database, **kwargs)

    def write_session(
        self,
        database: str | None = None,
        **kwargs: Any,
    ) -> Session:
        """Create a read-write session.

        Args:
            database: Database name.
            **kwargs: Additional session parameters.

        Returns:
            Neo4j Session instance in WRITE mode.
        """
        return self.session(mode=SessionMode.WRITE.value, database=database, **kwargs)

    # =========================================================================
    # Query Execution
    # =========================================================================

    def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
        timeout: int | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results.

        Args:
            query: Cypher query string.
            parameters: Query parameters.
            database: Database name.
            timeout: Query timeout in seconds.

        Returns:
            List of result records as dictionaries.

        Raises:
            QueryError: If query execution fails.
        """
        self._ensure_connected()
        params = parameters or {}
        query_timeout = timeout or self._config["default_query_timeout"]

        try:
            with self.session(database=database) as session:
                result = session.run(query, params, timeout=query_timeout)
                return [record.data() for record in result]
        except neo4j_exceptions.CypherSyntaxError as e:
            logger.error(f"Cypher syntax error: {e}")
            raise QueryError(query=query, reason=f"Syntax error: {e}")
        except neo4j_exceptions.CypherTypeError as e:
            logger.error(f"Cypher type error: {e}")
            raise QueryError(query=query, reason=f"Type error: {e}")
        except neo4j_exceptions.ClientError as e:
            logger.error(f"Cypher client error: {e}")
            raise QueryError(query=query, reason=str(e))
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise QueryError(query=query, reason=str(e))

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
        timeout: int | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a write query in a transaction.

        Args:
            query: Cypher query string.
            parameters: Query parameters.
            database: Database name.
            timeout: Query timeout in seconds.

        Returns:
            List of result records as dictionaries.

        Raises:
            QueryError: If query execution fails.
            TransactionError: If transaction fails.
        """
        self._ensure_connected()
        params = parameters or {}
        query_timeout = timeout or self._config["default_query_timeout"]

        try:
            with self.write_session(database=database) as session:
                result = session.execute_write(
                    lambda tx: list(tx.run(query, params, timeout=query_timeout).data())
                )
                return result
        except neo4j_exceptions.TransientError as e:
            logger.error(f"Transient error in write transaction: {e}")
            raise TransactionError(reason=str(e))
        except QueryError:
            raise
        except Exception as e:
            logger.error(f"Write transaction failed: {e}")
            raise TransactionError(reason=str(e))

    def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
        timeout: int | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a read query in a transaction.

        Args:
            query: Cypher query string.
            parameters: Query parameters.
            database: Database name.
            timeout: Query timeout in seconds.

        Returns:
            List of result records as dictionaries.

        Raises:
            QueryError: If query execution fails.
        """
        self._ensure_connected()
        params = parameters or {}
        query_timeout = timeout or self._config["default_query_timeout"]

        try:
            with self.read_session(database=database) as session:
                result = session.execute_read(
                    lambda tx: list(tx.run(query, params, timeout=query_timeout).data())
                )
                return result
        except QueryError:
            raise
        except Exception as e:
            logger.error(f"Read transaction failed: {e}")
            raise QueryError(query=query, reason=str(e))

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def execute_batch(
        self,
        query: str,
        batch_parameter_key: str,
        batch_data: list[dict[str, Any]],
        batch_size: int = 1000,
        database: str | None = None,
    ) -> int:
        """Execute a query in batches for large datasets.

        Args:
            query: Cypher query with $batch_parameter_key placeholder.
            batch_parameter_key: Parameter name for batch data.
            batch_data: List of data items to process in batches.
            batch_size: Number of items per batch.
            database: Database name.

        Returns:
            Total number of items processed.

        Raises:
            QueryError: If query execution fails.
        """
        self._ensure_connected()
        total_processed = 0

        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i : i + batch_size]
            try:
                with self.write_session(database=database) as session:
                    session.execute_write(
                        lambda tx: list(
                            tx.run(query, {batch_parameter_key: batch}).data()
                        )
                    )
                    total_processed += len(batch)
                    logger.debug(f"Processed batch {i // batch_size + 1}: {len(batch)} items")
            except Exception as e:
                logger.error(f"Batch failed at index {i}: {e}")
                raise QueryError(query=query, reason=f"Batch failed: {e}")

        return total_processed

    # =========================================================================
    # Health Check & Utilities
    # =========================================================================

    def health_check(self) -> dict[str, Any]:
        """Check connection health and return server info.

        Returns:
            Dictionary with health status and server information.
        """
        try:
            start_time = time.time()
            self._ensure_connected()

            # Get server info
            with self.session() as session:
                result = session.run("CALL dbms.components() YIELD name, versions, edition")
                record = result.single()

                latency = (time.time() - start_time) * 1000  # Convert to ms

                return {
                    "status": "healthy",
                    "connected": True,
                    "server_info": {
                        "name": record["name"] if record else "Neo4j",
                        "version": record["versions"][0] if record and record["versions"] else "unknown",
                        "edition": record["edition"] if record else "unknown",
                    },
                    "latency_ms": round(latency, 2),
                    "error": None,
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "server_info": {},
                "latency_ms": 0.0,
                "error": str(e),
            }

    def get_server_info(self) -> dict[str, Any]:
        """Get Neo4j server information.

        Returns:
            Dictionary containing server information.
        """
        result = self.execute_query("CALL dbms.components() YIELD name, versions, edition")
        if result:
            record = result[0]
            return {
                "name": record.get("name", "Neo4j"),
                "version": record.get("versions", ["unknown"])[0],
                "edition": record.get("edition", "unknown"),
            }
        return {}

    def get_database_name(self) -> str:
        """Get the default database name.

        Returns:
            Default database name from configuration.
        """
        return self._config["database"]

    @property
    def config(self) -> dict[str, Any]:
        """Get current configuration (without sensitive data)."""
        safe_config = self._config.copy()
        safe_config["password"] = "***"  # Hide password
        return safe_config

    def __enter__(self) -> Neo4jClient:
        """Context manager entry."""
        self._ensure_connected()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        # Don't close connection on exit - maintain singleton
        pass


# =============================================================================
# Helper functions for parsing Neo4j results
# =============================================================================


def parse_node(node: Node) -> dict[str, Any]:
    """Parse a Neo4j Node object to dictionary.

    Args:
        node: Neo4j Node object.

    Returns:
        Dictionary with node properties and metadata.
    """
    labels = list(node.labels)
    return {
        "id": node.element_id,
        "labels": labels,
        "label": labels[0] if labels else None,
        "properties": dict(node),
    }


def parse_relationship(rel: Relationship) -> dict[str, Any]:
    """Parse a Neo4j Relationship object to dictionary.

    Args:
        rel: Neo4j Relationship object.

    Returns:
        Dictionary with relationship properties and metadata.
    """
    return {
        "id": rel.element_id,
        "type": rel.type,
        "start_node_id": rel.start_node.element_id,
        "end_node_id": rel.end_node.element_id,
        "properties": dict(rel),
    }
