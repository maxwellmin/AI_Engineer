"""S3-compatible storage client using boto3.

This module provides a singleton S3 client wrapper for MinIO and AWS S3 operations.
"""

from __future__ import annotations

import logging
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from django.conf import settings

from apps.object_storage_controller.exceptions import (
    FileNotFoundError,
    S3BucketError,
    S3ConnectionError,
    S3DeleteError,
    S3DownloadError,
    S3UploadError,
)

logger = logging.getLogger(__name__)


class S3Client:
    """S3-compatible storage client (MinIO/AWS S3).

    This class implements the singleton pattern for connection reuse.
    Supports both MinIO (development) and AWS S3 (production).
    """

    _instance: S3Client | None = None
    _client: boto3.client | None = None
    _bucket_name: str = ""

    def __new__(cls) -> S3Client:
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self) -> None:
        """Initialize boto3 S3 client with settings."""
        try:
            # Build client configuration
            config = Config(
                signature_version="s3v4",
                retries={
                    "max_attempts": 3,
                    "mode": "standard",
                },
            )

            # Initialize boto3 client
            # endpoint_url is None for AWS S3 (uses default endpoints)
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL or None,
                aws_access_key_id=settings.S3_ACCESS_KEY_ID,
                aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
                region_name=settings.S3_REGION_NAME,
                config=config,
            )
            self._bucket_name = settings.S3_BUCKET_NAME

            logger.info(
                f"S3 client initialized for bucket '{self._bucket_name}' "
                f"(endpoint: {settings.S3_ENDPOINT_URL or 'AWS S3 default'})"
            )

        except NoCredentialsError as e:
            raise S3ConnectionError("S3 credentials not configured") from e
        except Exception as e:
            raise S3ConnectionError(f"Failed to initialize S3 client: {e}") from e

    @property
    def bucket_name(self) -> str:
        """Get the bucket name."""
        return self._bucket_name

    def upload_file(
        self,
        file_path: str,
        content: BinaryIO,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> str:
        """Upload file to S3.

        Args:
            file_path: Object key/path for the file
            content: Binary file content stream
            content_type: MIME type of the file
            metadata: Optional custom metadata

        Returns:
            ETag of the uploaded object

        Raises:
            S3UploadError: If upload fails
        """
        if self._client is None:
            raise S3ConnectionError("S3 client not initialized")

        try:
            extra_args: dict = {
                "ContentType": content_type,
            }
            if metadata:
                extra_args["Metadata"] = metadata

            self._client.upload_fileobj(
                content,
                self._bucket_name,
                file_path,
                ExtraArgs=extra_args,
            )

            # Get ETag from head object
            response = self._client.head_object(
                Bucket=self._bucket_name,
                Key=file_path,
            )
            etag = response.get("ETag", "").strip('"')

            logger.debug(f"Uploaded file '{file_path}' to S3 (ETag: {etag})")
            return etag

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise S3UploadError(f"Failed to upload '{file_path}': {error_code}") from e
        except Exception as e:
            raise S3UploadError(f"Failed to upload '{file_path}': {e}") from e

    def download_file(self, file_path: str) -> bytes:
        """Download file content from S3.

        Args:
            file_path: Object key/path of the file

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file does not exist
            S3DownloadError: If download fails
        """
        if self._client is None:
            raise S3ConnectionError("S3 client not initialized")

        try:
            response = self._client.get_object(
                Bucket=self._bucket_name,
                Key=file_path,
            )
            content = response["Body"].read()
            logger.debug(f"Downloaded file '{file_path}' from S3 ({len(content)} bytes)")
            return content

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey" or error_code == "404":
                raise FileNotFoundError(f"File not found: '{file_path}'") from e
            raise S3DownloadError(f"Failed to download '{file_path}': {error_code}") from e
        except Exception as e:
            raise S3DownloadError(f"Failed to download '{file_path}': {e}") from e

    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3.

        Args:
            file_path: Object key/path of the file

        Returns:
            True if file was deleted

        Raises:
            S3DeleteError: If delete fails
        """
        if self._client is None:
            raise S3ConnectionError("S3 client not initialized")

        try:
            self._client.delete_object(
                Bucket=self._bucket_name,
                Key=file_path,
            )
            logger.debug(f"Deleted file '{file_path}' from S3")
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise S3DeleteError(f"Failed to delete '{file_path}': {error_code}") from e
        except Exception as e:
            raise S3DeleteError(f"Failed to delete '{file_path}': {e}") from e

    def head_object(self, file_path: str) -> dict:
        """Get object metadata without downloading.

        Args:
            file_path: Object key/path of the file

        Returns:
            Dictionary with object metadata (ContentLength, ContentType, ETag, etc.)

        Raises:
            FileNotFoundError: If file does not exist
            StorageError: If operation fails
        """
        if self._client is None:
            raise S3ConnectionError("S3 client not initialized")

        try:
            response = self._client.head_object(
                Bucket=self._bucket_name,
                Key=file_path,
            )
            return {
                "size": response.get("ContentLength", 0),
                "content_type": response.get("ContentType", ""),
                "etag": response.get("ETag", "").strip('"'),
                "last_modified": response.get("LastModified"),
                "metadata": response.get("Metadata", {}),
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey" or error_code == "404":
                raise FileNotFoundError(f"File not found: '{file_path}'") from e
            raise S3DownloadError(f"Failed to get metadata for '{file_path}': {error_code}") from e

    def object_exists(self, file_path: str) -> bool:
        """Check if object exists in S3.

        Args:
            file_path: Object key/path of the file

        Returns:
            True if object exists, False otherwise
        """
        try:
            self.head_object(file_path)
            return True
        except FileNotFoundError:
            return False

    def generate_presigned_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        http_method: str = "GET",
    ) -> str:
        """Generate presigned URL for upload/download.

        Args:
            file_path: Object key/path of the file
            expires_in: URL expiry time in seconds
            http_method: HTTP method ('GET' for download, 'PUT' for upload)

        Returns:
            Presigned URL string

        Raises:
            StorageError: If URL generation fails
        """
        if self._client is None:
            raise S3ConnectionError("S3 client not initialized")

        try:
            client_method = "get_object" if http_method == "GET" else "put_object"
            url = self._client.generate_presigned_url(
                ClientMethod=client_method,
                Params={
                    "Bucket": self._bucket_name,
                    "Key": file_path,
                },
                ExpiresIn=expires_in,
            )
            logger.debug(
                f"Generated presigned URL for '{file_path}' "
                f"(method: {http_method}, expires_in: {expires_in}s)"
            )
            return url

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise S3ConnectionError(
                f"Failed to generate presigned URL for '{file_path}': {error_code}"
            ) from e

    def ensure_bucket_exists(self) -> bool:
        """Create bucket if not exists.

        Returns:
            True if bucket was created, False if already exists

        Raises:
            S3BucketError: If bucket creation fails
        """
        if self._client is None:
            raise S3ConnectionError("S3 client not initialized")

        try:
            # Check if bucket exists
            self._client.head_bucket(Bucket=self._bucket_name)
            logger.debug(f"Bucket '{self._bucket_name}' already exists")
            return False

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                # Bucket doesn't exist, create it
                try:
                    self._client.create_bucket(Bucket=self._bucket_name)
                    logger.info(f"Created bucket '{self._bucket_name}'")
                    return True
                except ClientError as create_error:
                    raise S3BucketError(
                        f"Failed to create bucket '{self._bucket_name}': {create_error}"
                    ) from create_error
            raise S3BucketError(f"Failed to check bucket: {error_code}") from e

    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> list[dict]:
        """List objects in bucket with optional prefix filter.

        Args:
            prefix: Filter objects by prefix
            max_keys: Maximum number of objects to return

        Returns:
            List of object metadata dictionaries
        """
        if self._client is None:
            raise S3ConnectionError("S3 client not initialized")

        try:
            response = self._client.list_objects_v2(
                Bucket=self._bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys,
            )

            objects = []
            for obj in response.get("Contents", []):
                objects.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                    "etag": obj["ETag"].strip('"'),
                })

            return objects

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            raise S3BucketError(f"Failed to list objects: {error_code}") from e

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
        cls._client = None
