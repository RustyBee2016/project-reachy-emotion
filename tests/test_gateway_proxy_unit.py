"""Unit tests for gateway status proxy handlers without TestClient."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip("httpx")

from apps.api.routers import gateway


class _DummyRequest:
    def __init__(self, payload: dict, http_client):
        self._payload = payload
        self.app = SimpleNamespace(
            state=SimpleNamespace(
                http_client=http_client,
                config=SimpleNamespace(media_mover_url="http://media-mover.local"),
            )
        )

    async def json(self):
        return self._payload


def _body(resp):
    return json.loads(resp.body.decode("utf-8"))


def test_get_training_status_proxy_unit():
    mocked = Mock(status_code=200)
    mocked.json.return_value = {"run_id": "abc", "status": "training"}
    http_client = SimpleNamespace(get=AsyncMock(return_value=mocked))

    req = _DummyRequest({}, http_client)
    resp = asyncio.run(gateway.get_training_status("abc", req))
    assert resp.status_code == 200
    assert _body(resp)["status"] == "training"


def test_update_deployment_status_proxy_unit():
    mocked = Mock(status_code=200)
    mocked.json.return_value = {"status": "updated", "pipeline_id": "pipe1"}
    http_client = SimpleNamespace(post=AsyncMock(return_value=mocked))

    req = _DummyRequest({"status": "deploying"}, http_client)
    resp = asyncio.run(gateway.update_deployment_status("pipe1", req))
    assert resp.status_code == 200
    assert _body(resp)["status"] == "updated"
