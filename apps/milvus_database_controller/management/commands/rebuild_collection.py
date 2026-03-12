"""
Django management command to rebuild Milvus collection with BM25 support.

This command:
1. Drops the existing collection (if exists)
2. Creates a new collection with BM25 Function enabled
3. Creates all indexes (dense + sparse)
4. Loads the collection into memory

Usage:
    python manage.py rebuild_collection [--collection COLLECTION_NAME] [--dimension DIMENSION]
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

from apps.milvus_database_controller.constants import (
    COLLECTION_DOCUMENTS,
    DEFAULT_DENSE_DIMENSION,
)
from apps.milvus_database_controller.managers.collection_manager import CollectionManager
from apps.milvus_database_controller.managers.index_manager import IndexManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Rebuild Milvus collection with BM25 support."""

    help = "Rebuild Milvus collection with BM25 Function enabled"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--collection",
            type=str,
            default=COLLECTION_DOCUMENTS,
            help=f"Collection name (default: {COLLECTION_DOCUMENTS})",
        )
        parser.add_argument(
            "--dimension",
            type=int,
            default=DEFAULT_DENSE_DIMENSION,
            help=f"Vector dimension (default: {DEFAULT_DENSE_DIMENSION})",
        )
        parser.add_argument(
            "--no-drop",
            action="store_true",
            help="Do not drop existing collection (will fail if collection exists)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        collection_name = options["collection"]
        dimension = options["dimension"]
        no_drop = options["no_drop"]

        self.stdout.write(f"Rebuilding collection '{collection_name}' with dimension {dimension}")

        collection_manager = CollectionManager()
        index_manager = IndexManager()

        # Step 1: Drop existing collection (if exists)
        if not no_drop:
            if collection_manager.has_collection(collection_name):
                self.stdout.write(f"Dropping existing collection '{collection_name}'...")
                try:
                    collection_manager.drop_collection(collection_name)
                    self.stdout.write(self.style.SUCCESS(f"Collection '{collection_name}' dropped"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Failed to drop collection: {e}"))
                    return
            else:
                self.stdout.write(f"Collection '{collection_name}' does not exist, will create new")
        else:
            if collection_manager.has_collection(collection_name):
                self.stderr.write(self.style.ERROR(
                    f"Collection '{collection_name}' already exists. "
                    "Use --no-drop only when creating new collection."
                ))
                return

        # Step 2: Create collection with BM25 Function
        self.stdout.write(f"Creating collection '{collection_name}' with BM25 Function...")
        try:
            from apps.milvus_database_controller.schemas.collection_schema import (
                get_document_collection_schema,
            )

            schema = get_document_collection_schema(
                dimension=dimension,
                enable_dynamic_field=True,
            )

            collection_manager.create_collection_with_schema(
                collection_name=collection_name,
                schema=schema,
                description=f"Documents collection with BM25 support (dimension={dimension})",
            )
            self.stdout.write(self.style.SUCCESS(f"Collection '{collection_name}' created with BM25 Function"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to create collection: {e}"))
            return

        # Step 3: Create indexes
        self.stdout.write("Creating indexes...")
        try:
            results = index_manager.create_all_indexes(collection_name)

            # Report results
            for index_name, success in results.items():
                if success:
                    self.stdout.write(self.style.SUCCESS(f"  Index '{index_name}' created"))
                else:
                    self.stdout.write(self.style.WARNING(f"  Index '{index_name}' creation failed"))

            # Check if all indexes created
            if all(results.values()):
                self.stdout.write(self.style.SUCCESS("All indexes created successfully"))
            else:
                self.stdout.write(self.style.WARNING("Some indexes failed to create"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to create indexes: {e}"))
            return

        # Step 4: Load collection into memory
        self.stdout.write(f"Loading collection '{collection_name}' into memory...")
        try:
            index_manager.load_collection(collection_name)
            self.stdout.write(self.style.SUCCESS(f"Collection '{collection_name}' loaded into memory"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to load collection: {e}"))
            return

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(f"Collection '{collection_name}' rebuilt successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("")
        self.stdout.write("Collection now includes:")
        self.stdout.write("  - text_sparse field for BM25 search")
        self.stdout.write("  - Dense vector fields (summary_dense, text_dense)")
        self.stdout.write("  - Sparse index for BM25 search")
        self.stdout.write("")
        self.stdout.write("Next steps:")
        self.stdout.write(f"  1. Re-run document pipeline to populate vectors")
        self.stdout.write(f"  2. Test BM25 search: POST /api/v1/milvus/search/bm25/")
        self.stdout.write(f"  3. Test hybrid search with include_sparse=true")
