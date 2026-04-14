from app.src.main import _shutdown_requested, create_app


def test_healthz_returns_ok() -> None:
    client = create_app().test_client()
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_livez_returns_live() -> None:
    client = create_app().test_client()
    response = client.get("/livez")

    assert response.status_code == 200
    assert response.json == {"status": "live"}


def test_readyz_returns_ready_when_running() -> None:
    _shutdown_requested.clear()
    client = create_app().test_client()
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json == {"status": "ready"}


def test_readyz_returns_503_during_shutdown() -> None:
    _shutdown_requested.set()
    client = create_app().test_client()
    response = client.get("/readyz")
    _shutdown_requested.clear()

    assert response.status_code == 503
    assert response.json["status"] == "not_ready"
