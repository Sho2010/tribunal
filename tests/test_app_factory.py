import pytest
from fastapi.testclient import TestClient

from tribunal.app_factory import create_app


def test_health_reports_enabled_platforms(slack_env: None) -> None:
    client = TestClient(create_app(["slack"], verify_credentials=False))

    res = client.get("/")

    assert res.status_code == 200
    assert res.json() == {"status": "ok", "platforms": ["slack"]}


def test_unknown_platform_raises() -> None:
    with pytest.raises(ValueError, match="unknown platform"):
        create_app(["discord"])


def test_slack_adapter_mounts_events_endpoint(slack_env: None) -> None:
    app = create_app(["slack"], verify_credentials=False)

    routes = {getattr(r, "path", None) for r in app.routes}

    assert "/slack/events" in routes


def test_no_platform_requires_no_platform_env() -> None:
    """有効化していない platform の依存 / env を要求しない（遅延 import の意図）。

    SLACK_* を一切用意していない状態でも create_app([]) が通ることで確認する。
    """
    client = TestClient(create_app([]))

    assert client.get("/").json() == {"status": "ok", "platforms": []}
