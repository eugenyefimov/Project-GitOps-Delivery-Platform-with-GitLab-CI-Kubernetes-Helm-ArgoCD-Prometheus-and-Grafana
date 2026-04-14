import json
import logging
import signal
import threading
import time
from datetime import datetime, timezone

from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

SERVICE_NAME = "platform-app"
SERVICE_VERSION = "0.1.0"
DEFAULT_PORT = 8080

_shutdown_requested = threading.Event()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "path"):
            payload["path"] = record.path
        if hasattr(record, "method"):
            payload["method"] = record.method
        if hasattr(record, "status_code"):
            payload["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = record.duration_ms
        if hasattr(record, "signal"):
            payload["signal"] = record.signal
        return json.dumps(payload)


def configure_logging() -> logging.Logger:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(SERVICE_NAME)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def create_app() -> Flask:
    app = Flask(__name__)
    logger = configure_logging()

    request_counter = Counter(
        "platform_app_http_requests_total",
        "Total number of HTTP requests by endpoint",
        ["endpoint", "method", "status_code"],
    )
    request_duration = Histogram(
        "platform_app_http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["endpoint", "method"],
    )
    in_flight_requests = Gauge(
        "platform_app_in_flight_requests",
        "Current number of in-flight HTTP requests",
    )

    @app.before_request
    def before_request() -> None:
        request.environ["request_start_time"] = time.perf_counter()
        in_flight_requests.inc()

    @app.after_request
    def after_request(response: Response) -> Response:
        start_time = request.environ.get("request_start_time")
        duration_s = 0.0
        if isinstance(start_time, float):
            duration_s = time.perf_counter() - start_time
        endpoint = request.path
        method = request.method
        status_code = str(response.status_code)
        request_counter.labels(endpoint=endpoint, method=method, status_code=status_code).inc()
        request_duration.labels(endpoint=endpoint, method=method).observe(duration_s)
        in_flight_requests.dec()
        logger.info(
            "request_completed",
            extra={
                "path": endpoint,
                "method": method,
                "status_code": response.status_code,
                "duration_ms": round(duration_s * 1000, 2),
            },
        )
        return response

    @app.get("/")
    def root() -> tuple[Response, int]:
        return (
            jsonify(
                {
                    "service": SERVICE_NAME,
                    "version": SERVICE_VERSION,
                    "status": "running",
                }
            ),
            200,
        )

    @app.get("/livez")
    def livez() -> tuple[Response, int]:
        return jsonify({"status": "live"}), 200

    @app.get("/readyz")
    def readyz() -> tuple[Response, int]:
        if _shutdown_requested.is_set():
            return jsonify({"status": "not_ready", "reason": "shutdown_in_progress"}), 503
        return jsonify({"status": "ready"}), 200

    @app.get("/healthz")
    def healthz() -> tuple[Response, int]:
        # Backward-compatible endpoint mapped to liveness semantics.
        return jsonify({"status": "ok"}), 200

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    return app


app = create_app()


def _handle_shutdown_signal(signum: int, _frame: object) -> None:
    _shutdown_requested.set()
    logging.getLogger(SERVICE_NAME).info("shutdown_signal_received", extra={"signal": signum})


signal.signal(signal.SIGTERM, _handle_shutdown_signal)
signal.signal(signal.SIGINT, _handle_shutdown_signal)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=DEFAULT_PORT)
