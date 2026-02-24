"""
Custom pagination classes for melon project.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Standard pagination class with configurable page size.

    Response format:
    {
        "success": true,
        "data": [...],
        "pagination": {
            "count": 100,
            "page": 1,
            "page_size": 20,
            "total_pages": 5,
            "has_next": true,
            "has_previous": false
        }
    }
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data: list[Any]) -> Response:
        """
        Return a paginated response with standard format.

        Args:
            data: The paginated data list

        Returns:
            Response with standard envelope format
        """
        total_pages = self.page.paginator.num_pages

        return Response(
            {
                "success": True,
                "data": data,
                "pagination": {
                    "count": self.page.paginator.count,
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total_pages": total_pages,
                    "has_next": self.page.has_next(),
                    "has_previous": self.page.has_previous(),
                },
            }
        )


class SmallPagination(PageNumberPagination):
    """
    Small pagination for lists with fewer items (e.g., comments, tags).

    Uses a smaller default page size of 10.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data: list[Any]) -> Response:
        """Return a paginated response with small pagination."""
        return Response(
            {
                "success": True,
                "data": data,
                "pagination": {
                    "count": self.page.paginator.count,
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total_pages": self.page.paginator.num_pages,
                    "has_next": self.page.has_next(),
                    "has_previous": self.page.has_previous(),
                },
            }
        )


class LargePagination(PageNumberPagination):
    """
    Large pagination for bulk data exports or large datasets.

    Uses a larger default page size of 100.
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500

    def get_paginated_response(self, data: list[Any]) -> Response:
        """Return a paginated response with large pagination."""
        return Response(
            {
                "success": True,
                "data": data,
                "pagination": {
                    "count": self.page.paginator.count,
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total_pages": self.page.paginator.num_pages,
                    "has_next": self.page.has_next(),
                    "has_previous": self.page.has_previous(),
                },
            }
        )
