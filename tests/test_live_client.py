import json

import pytest

from oraculo.live import client as cl


def test_get_matches_fetches_and_caches(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_fetch(url, token):
        calls["n"] += 1
        return {"matches": [{"id": 1}]}

    monkeypatch.setattr(cl, "_http_get_json", fake_fetch)
    c = cl.LiveClient(token="x", cache_dir=tmp_path, ttl_seconds=999)

    a = c.get_matches()
    b = c.get_matches()  # segunda llamada: usa cache, no re-fetch
    assert a == b == {"matches": [{"id": 1}]}
    assert calls["n"] == 1
    assert (tmp_path / "matches.json").exists()


def test_offline_uses_stale_cache_when_fetch_fails(tmp_path, monkeypatch):
    (tmp_path / "matches.json").write_text(json.dumps({"matches": [{"id": 9}]}), encoding="utf-8")

    def boom(url, token):
        raise OSError("sin internet")

    monkeypatch.setattr(cl, "_http_get_json", boom)
    # ttl=0 fuerza el re-fetch, que falla -> debe caer al cache viejo
    c = cl.LiveClient(token="x", cache_dir=tmp_path, ttl_seconds=0)
    assert c.get_matches() == {"matches": [{"id": 9}]}


def test_raises_when_no_token_and_no_cache(tmp_path, monkeypatch):
    def boom(url, token):
        raise OSError("sin internet")

    monkeypatch.setattr(cl, "_http_get_json", boom)
    c = cl.LiveClient(token=None, cache_dir=tmp_path, ttl_seconds=0)
    with pytest.raises(cl.LiveDataError):
        c.get_matches()
