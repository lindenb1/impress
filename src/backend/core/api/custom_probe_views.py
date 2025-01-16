"""API liveness and readiness probes for Impress' core application."""

import uuid

import requests
from botocore.exceptions import BotoCoreError, ClientError
from django.core.cache import CacheKeyWarning, cache
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponse, HttpResponseServerError, JsonResponse

from impress import settings


def liveness_check(request):
    """
    Liveness probe endpoint.
    Returns HTTP 200 if the application is alive and running.
    """

    return JsonResponse({"status": "OK"}, status=200)


def readiness_check(request):
    """
    Readiness probe endpoint.
    Checks database, cache, media storage, and OIDC configuration.
    Returns HTTP 200 with JSON status "OK" if all checks pass,
    or HTTP 500 with JSON status "Error" and an error message.
    """

    def check_database():
        """Check database connectivity."""
        try:
            db_conn = connections["default"]
            db_conn.cursor()
        except OperationalError as e:
            # Chain the original error
            raise Exception("Database check failed") from e

    def check_cache():
        """Check cache connectivity."""
        test_key = "readiness-probe"
        test_value = "ready"
        cache.set(test_key, test_value, timeout=5)
        if cache.get(test_key) != test_value:
            raise Exception("Cache check failed: Value mismatch or cache unavailable")

    def check_media_storage():
        """Check S3 storage connectivity by attempting to write and delete a test file."""
        test_file_name = f"readiness-check-{uuid.uuid4()}.txt"
        test_content = ContentFile(b"readiness check")

        try:
            # Attempt to save the test file
            default_storage.save(test_file_name, test_content)
            # Attempt to delete the test file
            default_storage.delete(test_file_name)
        except (SuspiciousFileOperation, OSError, BotoCoreError, ClientError) as e:
            # Re-raise with context from the original exception
            raise RuntimeError("Media storage check failed.") from e

    def check_oidc():
        """Check OIDC configuration and connectivity."""
        required_endpoints = [
            ("OIDC_OP_JWKS_ENDPOINT", settings.OIDC_OP_JWKS_ENDPOINT),
            ("OIDC_OP_TOKEN_ENDPOINT", settings.OIDC_OP_TOKEN_ENDPOINT),
            ("OIDC_OP_USER_ENDPOINT", settings.OIDC_OP_USER_ENDPOINT),
        ]

        # If any required endpoints are missing, raise a specific exception.
        missing_endpoints = [name for name, url in required_endpoints if not url]
        if missing_endpoints:
            raise RuntimeError(
                f"Missing OIDC configuration for: {', '.join(missing_endpoints)}"
            )

        # Check connectivity to each endpoint.
        for name, url in required_endpoints:
            try:
                requests.get(url, timeout=5)
            except requests.RequestException as e:
                # Re-raise with the original exception context.
                raise RuntimeError(f"Failed to reach {name} at {url}") from e

    try:
        # Run all checks
        check_database()
        check_cache()
        check_media_storage()
        check_oidc()

        # If all checks pass
        return JsonResponse({"status": "OK"}, status=200)

    except (
        OperationalError,
        CacheKeyWarning,
        BotoCoreError,
        ClientError,
        requests.RequestException,
    ) as e:
        return JsonResponse({"status": "Error", "message": str(e)}, status=500)
