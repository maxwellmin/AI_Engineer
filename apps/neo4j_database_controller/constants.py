"""
Constants for Neo4j database controller.

This module defines all constant values used across the Neo4j database controller,
including node labels, relationship types, property names, and configuration defaults.
"""

from __future__ import annotations

from enum import Enum


# =============================================================================
# Node Labels
# =============================================================================


class NodeLabel(str, Enum):
    """Node labels for Neo4j graph.

    These labels categorize nodes in the knowledge graph:
    - Document: Source documents (PDF, DOCX, etc.)
    - Chunk: Text chunks extracted from documents
    - Entity: Named entities (people, organizations, locations, etc.)
    - Concept: Abstract concepts and topics
    - User: User nodes linked to PostgreSQL
    """

    DOCUMENT = "Document"
    CHUNK = "Chunk"
    ENTITY = "Entity"
    CONCEPT = "Concept"
    USER = "User"


# Valid node labels for validation
VALID_NODE_LABELS: list[str] = [label.value for label in NodeLabel]


# =============================================================================
# Relationship Types
# =============================================================================


class RelType(str, Enum):
    """Relationship types for Neo4j graph.

    These relationships define how nodes are connected:
    - CONTAINS: Document -> Chunk (document contains text chunk)
    - MENTIONS: Chunk -> Entity (chunk mentions an entity)
    - RELATED_TO: Entity -> Entity (entities are related)
    - ABOUT: Document -> Concept (document is about a concept)
    - ASKED: User -> Question (user asked a question)
    - ANSWERED_BY: Question -> Chunk (question answered by chunk)
    """

    CONTAINS = "CONTAINS"  # Document -> Chunk
    MENTIONS = "MENTIONS"  # Chunk -> Entity
    RELATED_TO = "RELATED_TO"  # Entity -> Entity
    ABOUT = "ABOUT"  # Document -> Concept
    ASKED = "ASKED"  # User -> Question
    ANSWERED_BY = "ANSWERED_BY"  # Question -> Chunk


# Valid relationship types for validation
VALID_REL_TYPES: list[str] = [rel.value for rel in RelType]


# =============================================================================
# Property Names
# =============================================================================


class PropName:
    """Property names for nodes and relationships.

    This class defines standard property names used throughout the graph schema.
    Using constants ensures consistency and reduces errors.
    """

    # Common properties
    ID = "id"
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

    # Document properties
    TITLE = "title"
    SOURCE = "source"
    DOC_TYPE = "doc_type"
    STATUS = "status"

    # Chunk properties
    TEXT = "text"
    CHUNK_INDEX = "chunk_index"
    PAGE_NUMBER = "page_number"
    START_CHAR = "start_char"
    END_CHAR = "end_char"
    DOCUMENT_ID = "document_id"

    # Entity properties
    ENTITY_TYPE = "entity_type"
    DESCRIPTION = "description"
    CONFIDENCE = "confidence"

    # Concept properties
    CATEGORY = "category"

    # Relationship properties
    RELATION_TYPE = "relation_type"
    COUNT = "count"
    ORDER = "order"


# =============================================================================
# Entity Types
# =============================================================================


class EntityType(str, Enum):
    """Entity types for extraction.

    These types categorize named entities extracted from text:
    - PERSON: People and individuals
    - ORGANIZATION: Companies, institutions, groups
    - LOCATION: Geographic locations, addresses
    - TECHNOLOGY: Technologies, programming languages, tools
    - EVENT: Events, conferences, meetings
    - DATE: Dates and time references
    - MONEY: Monetary values
    - PRODUCT: Products and services
    - CONCEPT: Abstract concepts and ideas
    """

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    TECHNOLOGY = "technology"
    EVENT = "event"
    DATE = "date"
    MONEY = "money"
    PRODUCT = "product"
    CONCEPT = "concept"


# Valid entity types for validation
VALID_ENTITY_TYPES: list[str] = [et.value for et in EntityType]


# =============================================================================
# Default Configuration Values
# =============================================================================

# Query defaults
DEFAULT_MAX_DEPTH = 5  # Maximum depth for graph traversal
DEFAULT_BATCH_SIZE = 1000  # Default batch size for bulk operations
DEFAULT_QUERY_TIMEOUT = 60  # seconds
DEFAULT_CONNECTION_TIMEOUT = 30  # seconds

# Connection pool defaults
DEFAULT_MAX_CONNECTION_POOL_SIZE = 50
DEFAULT_MAX_TRANSACTION_RETRY_TIME = 30  # seconds


# =============================================================================
# Direction for Relationship Traversal
# =============================================================================


class Direction(str, Enum):
    """Direction for relationship traversal.

    Used in graph queries to specify relationship direction:
    - OUTGOING: Follow relationships from source to target
    - INCOMING: Follow relationships from target to source
    - BOTH: Follow relationships in both directions
    """

    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"
    BOTH = "BOTH"


# =============================================================================
# Session Modes
# =============================================================================


class SessionMode(str, Enum):
    """Session access modes for Neo4j.

    - WRITE: Read-write session (can perform all operations)
    - READ: Read-only session (for queries only)
    """

    WRITE = "WRITE"
    READ = "READ"


# =============================================================================
# Error Messages
# =============================================================================

ERROR_NODE_NOT_FOUND = "Node '{node_id}' (label: {label}) not found"
ERROR_RELATIONSHIP_NOT_FOUND = "Relationship {rel_id} not found"
ERROR_CONNECTION_FAILED = "Failed to connect to Neo4j server: {reason}"
ERROR_QUERY_FAILED = "Query failed: {reason}"
ERROR_CONSTRAINT_VIOLATION = "Constraint violation '{constraint}': {reason}"
ERROR_INVALID_NODE_LABEL = "Invalid node label '{label}'. Valid labels: {valid_labels}"
ERROR_INVALID_REL_TYPE = "Invalid relationship type '{rel_type}'. Valid types: {valid_types}"
ERROR_INVALID_ENTITY_TYPE = "Invalid entity type '{entity_type}'. Valid types: {valid_types}"
ERROR_BATCH_INSERT_FAILED = "Failed to insert batch: {reason}"
ERROR_TRANSACTION_FAILED = "Transaction failed: {reason}"
