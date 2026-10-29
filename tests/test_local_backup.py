"""Tests for validating local backup manifests before archive restore."""

from collections.abc import Callable

import pytest

from scripts.local_backup import STATEFUL_VOLUMES, validate_manifest


def make_manifest() -> dict[str, object]:
    return {
        "format_version": 1,
        "project_name": "proofpoint-rag",
        "services": {
            service: {
                "volume_name": f"proofpoint-rag_{service}-data",
                "archive": f"{service}.tar.gz",
            }
            for service in STATEFUL_VOLUMES
        },
    }


def test_validate_manifest_accepts_all_expected_stateful_volumes() -> None:
    services = validate_manifest(make_manifest(), "proofpoint-rag")

    assert set(services) == set(STATEFUL_VOLUMES)
    assert services["postgres"]["archive"] == "postgres.tar.gz"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda value: value.update(format_version=2), "version"),
        (lambda value: value.update(project_name="another-project"), "different Compose project"),
        (lambda value: _services(value).pop("qdrant"), "exactly"),
        (
            lambda value: _service(value, "postgres").update(archive="../restore.tar.gz"),
            "archive",
        ),
    ],
)
def test_validate_manifest_rejects_mismatched_or_unsafe_entries(
    change: Callable[[dict[str, object]], object], message: str
) -> None:
    manifest = make_manifest()
    change(manifest)

    with pytest.raises(ValueError, match=message):
        validate_manifest(manifest, "proofpoint-rag")


def test_validate_manifest_rejects_non_object_input() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        validate_manifest([], "proofpoint-rag")


def _services(value: dict[str, object]) -> dict[str, object]:
    services = value["services"]
    assert isinstance(services, dict)
    return services


def _service(value: dict[str, object], name: str) -> dict[str, object]:
    service = _services(value)[name]
    assert isinstance(service, dict)
    return service
