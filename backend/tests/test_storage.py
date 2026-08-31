"""Object storage — presigning in particular.

Download links are the one place where the address the API uses and the address
the browser uses are not the same. Under Compose the API reaches MinIO at
`http://minio:9000`, a name that only resolves on the Docker network; signing
with it produced links every browser failed to load, and the dashboard showed
"Could not load image" for every photograph.
"""

from urllib.parse import urlparse

import pytest

from app.core.config import settings
from app.services import storage


@pytest.fixture
def restore_endpoints():
    """Settings are a process-wide singleton; put them back afterwards."""
    original = (settings.s3_endpoint_url, settings.s3_public_endpoint_url)
    yield
    settings.s3_endpoint_url, settings.s3_public_endpoint_url = original


def test_presigned_url_uses_public_endpoint(restore_endpoints) -> None:
    """The signed link must carry the host the browser can reach."""
    settings.s3_endpoint_url = "http://minio:9000"
    settings.s3_public_endpoint_url = "http://localhost:9000"

    url = storage.presigned_url("inspections/x/deck.jpg")

    assert urlparse(url).netloc == "localhost:9000"
    # The internal name must not survive anywhere in the link, including the
    # signed-headers and credential parameters.
    assert "minio:9000" not in url


def test_presigned_url_falls_back_to_the_api_endpoint(restore_endpoints) -> None:
    """Unset, presigning uses the same endpoint as everything else.

    This is the correct behaviour outside containers, where the API and the
    browser both reach MinIO on localhost.
    """
    settings.s3_endpoint_url = "http://localhost:9000"
    settings.s3_public_endpoint_url = None

    url = storage.presigned_url("inspections/x/deck.jpg")

    assert urlparse(url).netloc == "localhost:9000"


def test_presigned_url_is_signed(restore_endpoints) -> None:
    """A link without a signature would be a public object, not a timed one."""
    settings.s3_public_endpoint_url = "http://localhost:9000"

    url = storage.presigned_url("inspections/x/deck.jpg", expires_in=120)

    assert "X-Amz-Signature=" in url
    assert "X-Amz-Expires=120" in url
