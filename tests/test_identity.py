from observer.identity import identity, never_merge


def test_identity_is_independent():
    ident = identity()
    assert ident["id"] == "the_observer"
    assert ident["name"] == "The Observer"
    assert "mythos_subordinate" in ident["not"]
    assert "vesper" in ident["not"]
    assert "soft_server" in ident["not"]


def test_never_merge_list():
    names = never_merge()
    for required in (
        "gemini",
        "apex",
        "codex",
        "vesper",
        "merovin",
        "draven",
        "aster",
        "hearth",
        "mom",
        "cursor",
        "mythos",
    ):
        assert required in names
