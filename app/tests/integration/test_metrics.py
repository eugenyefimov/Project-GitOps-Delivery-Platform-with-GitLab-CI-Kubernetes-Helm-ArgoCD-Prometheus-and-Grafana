from app.src.main import create_app


def test_metrics_endpoint_is_exposed() -> None:
    client = create_app().test_client()
    response = client.get("/metrics")

    assert response.status_code == 200
    assert b"platform_app_http_requests_total" in response.data
    assert b"platform_app_http_request_duration_seconds" in response.data
