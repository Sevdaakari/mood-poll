from fastapi.testclient import TestClient

import main


def make_client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "test.db"))
    return TestClient(main.app)


def test_health(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.get("/health").json() == {"status": "ok"}


def test_vote_is_counted(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    client.post("/vote", json={"answer": "good"})
    client.post("/vote", json={"answer": "good"})
    client.post("/vote", json={"answer": "bad"})

    stats = client.get("/stats").json()
    assert stats["total"] == 3
    assert stats["counts"]["good"] == 2
    assert stats["percents"]["good"] == 67


def test_invalid_answer_is_rejected(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.post("/vote", json={"answer": "amazing"}).status_code == 422