"""Source universe: searchable ≠ truthful. No approved-news whitelist."""

from __future__ import annotations

import pytest

from observer.registry import get_capability, list_no_immunity
from observer.source_universe import (
    SOURCE_NETWORKS,
    NewsWhitelistForbidden,
    classify_source_class,
    classify_source_network,
    discovery_vs_evidence,
    independence_groups,
    network_search_status,
    refuse_news_only_gate,
)


def test_source_networks_include_decentralized_and_youtube_github():
    for name in ("FREENET", "I2P", "TOR_PUBLIC", "IPFS", "YOUTUBE", "PUBLIC_GIT", "PUBLIC_WEB"):
        assert name in SOURCE_NETWORKS


def test_classify_youtube_github_freenet_i2p_tor_ipfs():
    assert classify_source_network("https://www.youtube.com/watch?v=abc") == "YOUTUBE"
    assert classify_source_network("https://github.com/org/repo") == "PUBLIC_GIT"
    assert classify_source_network("freenet:CHK@example") == "FREENET"
    assert classify_source_network("http://example.i2p/page") == "I2P"
    assert classify_source_network("http://abcxyz.onion/pub") == "TOR_PUBLIC"
    assert classify_source_network("ipfs://bafyexample") == "IPFS"
    assert classify_source_class("https://www.youtube.com/watch?v=abc") == "VIDEO"
    assert classify_source_class("https://github.com/org/repo") == "TECHNICAL"


def test_unavailable_network_is_not_searched_not_false():
    status = network_search_status("FREENET")
    assert "NOT SEARCHED" in status
    assert "no Freenet evidence" not in status.lower()


def test_news_only_gate_is_forbidden():
    with pytest.raises(NewsWhitelistForbidden):
        refuse_news_only_gate(["NEWS_MEDIA"])
    refuse_news_only_gate(["NEWS_MEDIA", "COURT", "VIDEO", "TECHNICAL"])


def test_discovery_source_is_not_evidence_source():
    rel = discovery_vs_evidence(
        discovery_uri="https://duckduckgo.com/?q=x",
        article_uri="https://news.example/story",
        primary_uri="https://court.example/opinion/1",
    )
    assert rel["independent_count"] == 1
    assert rel["discovery_source"] != rel["evidence_source"]


def test_ten_copies_are_one_origin():
    uris = [f"https://mirror{i}.example/same-ap-story" for i in range(10)]
    origin = {u: "ap:wire-123" for u in uris}
    grouped = independence_groups(uris, origin_map=origin)
    assert grouped["independent_count"] == 1
    assert grouped["copy_count"] == 9
    assert grouped["independent_corroboration"] is False


def test_anonymous_and_decentralized_are_not_auto_rejected_or_trusted():
    assert classify_source_class("freenet:CHK@x") == "DECENTRALIZED"
    # Classification is not a truth verdict.
    assert classify_source_network("https://cnn.com/story") == "PUBLIC_WEB"


def test_registry_records_universe_and_unavailable_adapters(db):
    assert get_capability("source_universe")["status"] == "connected"
    assert get_capability("epistemic_integrity")["status"] == "connected"
    assert get_capability("freenet_adapter")["status"] == "unavailable"
    assert get_capability("i2p_adapter")["status"] == "unavailable"
    assert get_capability("tor_public_adapter")["status"] == "unavailable"
    assert get_capability("ipfs_adapter")["status"] == "unavailable"
    cats = {row["category"] for row in list_no_immunity()}
    assert "the_observer" in cats
    assert "observer_creator" in cats
