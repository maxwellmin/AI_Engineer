"""
DRF Serializers for Pipeline API.

This module provides serializers for pipeline request validation
and response serialization.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.document_pipeline_manager.models import PipelineExecution, PipelineStep


class ExecutePipelineSerializer(serializers.Serializer):
    """Serializer for pipeline execution request."""

    document_id = serializers.UUIDField(
        help_text="UUID of the document to process",
    )


class RetryPipelineSerializer(serializers.Serializer):
    """Serializer for pipeline retry request."""

    document_id = serializers.UUIDField(
        help_text="UUID of the document",
    )
    step_name = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Optional specific step to retry. If null, retries from failed step.",
    )


class CancelPipelineSerializer(serializers.Serializer):
    """Serializer for pipeline cancel request."""

    document_id = serializers.UUIDField(
        help_text="UUID of the document",
    )


class PipelineStepSerializer(serializers.Serializer):
    """Serializer for pipeline step details."""

    step_name = serializers.CharField()
    step_order = serializers.IntegerField()
    status = serializers.CharField()
    duration_ms = serializers.IntegerField()
    error_message = serializers.CharField(allow_blank=True)
    output_data = serializers.DictField(required=False)


class PipelineStatusSerializer(serializers.Serializer):
    """Serializer for pipeline status response."""

    document_id = serializers.UUIDField()
    status = serializers.CharField()
    current_step = serializers.CharField(allow_blank=True)
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    total_duration_ms = serializers.IntegerField()
    steps = PipelineStepSerializer(many=True)
    error_message = serializers.CharField(allow_blank=True)
    retry_count = serializers.IntegerField()


class PipelineHistorySerializer(serializers.Serializer):
    """Serializer for pipeline history response."""

    document_id = serializers.UUIDField()
    executions = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of execution records",
    )
    total_count = serializers.IntegerField()


class PipelineHealthSerializer(serializers.Serializer):
    """Serializer for pipeline health response."""

    status = serializers.CharField()
    database_connected = serializers.BooleanField()
    milvus_connected = serializers.BooleanField()
    neo4j_connected = serializers.BooleanField()
    active_pipelines = serializers.IntegerField()


class PipelineSummarySerializer(serializers.Serializer):
    """Serializer for pipeline summary response."""

    document_id = serializers.UUIDField()
    status = serializers.CharField()
    current_step = serializers.CharField(allow_blank=True)
    progress = serializers.DictField()
    error = serializers.DictField(allow_null=True)
    timing = serializers.DictField()


class RecentExecutionSerializer(serializers.Serializer):
    """Serializer for recent execution list item."""

    execution_id = serializers.UUIDField()
    document_id = serializers.UUIDField()
    status = serializers.CharField()
    current_step = serializers.CharField(allow_blank=True)
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    total_duration_ms = serializers.IntegerField()
    error_message = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class PipelineExecutionModelSerializer(serializers.ModelSerializer):
    """Model serializer for PipelineExecution."""

    class Meta:
        model = PipelineExecution
        fields = [
            "id",
            "document",
            "status",
            "current_step",
            "started_at",
            "completed_at",
            "total_duration_ms",
            "error_message",
            "error_step",
            "retry_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PipelineStepModelSerializer(serializers.ModelSerializer):
    """Model serializer for PipelineStep."""

    class Meta:
        model = PipelineStep
        fields = [
            "id",
            "execution",
            "step_name",
            "step_order",
            "status",
            "started_at",
            "completed_at",
            "duration_ms",
            "input_data",
            "output_data",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields
