import pytest

from observer.core import RegistryStatus
from observer.registry import (
    cannot_promote_unavailable_without_proof,
    get_capability,
    list_no_immunity,
    list_registry,
    mark_connected,
)
from observer.research.unavailable import four_reviewers


def test_registry_has_connected_and_unavailable(db):
    caps = {row["id"]: row for row in list_registry()}
    assert caps["identity"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["http_fetch"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["wayback"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["contradiction_engine"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["court_records"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["corporate_registries"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["sec_filings"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["patents"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["procurement"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["public_submission"]["status"] == RegistryStatus.CONNECTED.value
    assert caps["four_reviewers"]["status"] == RegistryStatus.UNAVAILABLE.value
    assert caps["auto_publish"]["status"] == RegistryStatus.DISABLED.value
    assert caps["mythos_supervisor"]["status"] == RegistryStatus.DISABLED.value
    assert caps["vesper_supervisor"]["status"] == RegistryStatus.DISABLED.value
    assert caps["ollama_extractor"]["status"] == RegistryStatus.UNAVAILABLE.value


def test_cannot_mark_disabled_connected(db):
    with pytest.raises(PermissionError):
        mark_connected("auto_publish", "should fail")


def test_unavailable_must_not_be_treated_as_wired(db):
    with pytest.raises(PermissionError):
        cannot_promote_unavailable_without_proof("four_reviewers")
    cannot_promote_unavailable_without_proof("identity")
    assert get_capability("four_reviewers")["status"] == "unavailable"


def test_unavailable_adapter_does_not_fetch(db):
    hits = four_reviewers.search("anything")
    assert hits[0]["failed"] is True
    with pytest.raises(RuntimeError):
        four_reviewers.fetch("https://example.com")


def test_no_immunity_includes_observer_and_mythos(db):
    cats = {row["category"] for row in list_no_immunity()}
    assert "the_observer" in cats
    assert "mythos" in cats
    assert "vesper" in cats
    assert "media" in cats
    assert "hollywood" in cats
