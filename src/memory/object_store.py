"""S3 interface for object storage"""

from typing import Optional, BinaryIO
from abc import ABC, abstractmethod
import boto3
from botocore.exceptions import ClientError


class ObjectStore(ABC):
    """Abstract interface for object storage"""

    @abstractmethod
    async def upload(
        self,
        key: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Upload an object"""
        pass

    @abstractmethod
    async def download(self, key: str) -> Optional[bytes]:
        """Download an object"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete an object"""
        pass

    @abstractmethod
    async def list(self, prefix: Optional[str] = None) -> list:
        """List objects with optional prefix"""
        pass


class S3ObjectStore(ObjectStore):
    """S3 implementation of object storage"""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None
    ):
        """
        Initialize S3 client

        Args:
            bucket: S3 bucket name
            region: AWS region
            endpoint_url: S3 endpoint (None for production, localstack URL for testing)
        """
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url

        self.client = boto3.client(
            's3',
            region_name=region,
            endpoint_url=endpoint_url
        )

    async def upload(
        self,
        key: str,
        content: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Upload an object to S3"""
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if metadata:
            extra_args["Metadata"] = metadata

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                **extra_args
            )
            return True
        except ClientError as e:
            raise RuntimeError(f"S3 upload error: {str(e)}") from e

    async def download(self, key: str) -> Optional[bytes]:
        """Download an object from S3"""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise RuntimeError(f"S3 download error: {str(e)}") from e

    async def delete(self, key: str) -> bool:
        """Delete an object from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            raise RuntimeError(f"S3 delete error: {str(e)}") from e

    async def list(self, prefix: Optional[str] = None) -> list:
        """List objects in S3 with optional prefix"""
        try:
            kwargs = {"Bucket": self.bucket}
            if prefix:
                kwargs["Prefix"] = prefix

            response = self.client.list_objects_v2(**kwargs)
            objects = response.get("Contents", [])
            return [obj["Key"] for obj in objects]
        except ClientError as e:
            raise RuntimeError(f"S3 list error: {str(e)}") from e
