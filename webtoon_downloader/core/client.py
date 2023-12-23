from __future__ import annotations

import random
from dataclasses import dataclass, field

import httpx

# List of user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.1; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.91",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.91",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
]


@dataclass
class WebtoonClient:
    http_client: httpx.AsyncClient
    user_agents: list[str] = field(default_factory=lambda: USER_AGENTS)

    async def __aenter__(self) -> WebtoonClient:
        return self

    async def __aexit__(self, *_: tuple) -> None:
        await self.http_client.aclose()

    async def get(self, url: str) -> httpx.Response:
        return await self.http_client.get(url, headers=self._generate_headers())

    def _generate_headers(self) -> dict:
        return {
            "accept-language": "en-US,en;q=0.9",
            "dnt": "1",
            "user-agent": random.choice(self.user_agents),
        }


@dataclass
class WebtoonViewerClient(WebtoonClient):
    async def get(self, url: str) -> httpx.Response:
        headers = self._generate_viewer_headers()
        return await self.http_client.get(url, headers=headers)

    def _generate_viewer_headers(self) -> dict:
        headers = super()._generate_headers()
        headers["referer"] = "https://www.webtoons.com/"
        return headers