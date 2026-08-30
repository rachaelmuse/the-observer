from __future__ import annotations

import httpx

_RealClient = httpx.Client


def mock_client_factory(html: str):
    def factory(*args, **kwargs):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text=html,
                headers={"content-type": "text/html; charset=utf-8"},
                request=request,
            )

        kwargs["transport"] = httpx.MockTransport(handler)
        return _RealClient(*args, **kwargs)

    return factory
