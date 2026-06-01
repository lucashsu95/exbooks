"""
Custom MinIO S3 storage backend for Exbooks.

Extends S3Boto3Storage to generate /media/ URLs compatible with nginx proxy.
This keeps existing templates working with {{ photo.image.url }} while
routing media requests through nginx → MinIO.
"""

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class MinioStorage(S3Boto3Storage):
    """MinIO S3 storage backend.

    Stores files in MinIO but generates /media/ URLs so nginx can
    proxy them transparently without exposing the internal MinIO endpoint.
    """

    def url(self, name):
        """Return a /media/ relative URL for nginx proxy routing."""
        return f"{settings.MEDIA_URL}{name}"
