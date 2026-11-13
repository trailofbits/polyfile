"""Fields shared by the committed compression-fixture provenance manifests."""

from typing import TypedDict


class FixtureProvenance(TypedDict):
    fixture: str
    payload: str
    encoded_sha256: str
    decoded_sha256: str
