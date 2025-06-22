from __future__ import annotations

import logging
import random
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncGenerator, Literal

import httpx
from httpx_retries import Retry, RetryTransport

from webtoon_downloader.core.exceptions import ImageDownloadError, RateLimitedError

log = logging.getLogger(__name__)

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
"""
List of random user agents
"""

MOBILE_USER_AGENTS = [
    """Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/114.0.5735.99 Mobile/15E148 Safari/604.1""",
    """Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/114.0.5735.124 Mobile/15E148 Safari/604.1""",
    """Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/114.1 Mobile/15E148 Safari/605.1.15""",
    """Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36""",
    """Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/21.0 Chrome/110.0.5481.154 Mobile Safari/537.36""",
]
"""
List of random user agents of mobiles
"""

WebtoonURL = "https://www.webtoons.com"
WebtoonMobileURL = "https://m.webtoons.com"

RetryStrategy = Literal["exponential", "linear", "fixed"]


@dataclass
class WebtoonHttpClient:
    """
    An asynchronous HTTP client configured for scrapping webtoon website.

    The client uses HTTP/2, custom headers with a randomly selected user agent,
    and is configured with high limits for maximum connections and keep-alive connections.
    """

    proxy: str | None = None
    retry_strategy: RetryStrategy | None = None

    _client: httpx.AsyncClient = field(init=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=200),
            http2=True,
            headers=self._generate_headers(),
            follow_redirects=True,
            proxy=self.proxy,
            transport=self._build_transport(),
        )

    def _build_transport(self) -> httpx.AsyncBaseTransport:
        base_transport = httpx.AsyncHTTPTransport(http2=True)
        if self.retry_strategy is None:
            log.warning("No retry strategy provided; using default transport without retry")
            return base_transport

        # retry_on_exceptions = (*httpx_retries.Retry.RETRYABLE_EXCEPTIONS, h2.exceptions.InvalidBodyLengthError)
        max_retries = 20
        retry = {
            "exponential": Retry(total=max_retries, backoff_factor=0.25, respect_retry_after_header=True),
            "linear": Retry(total=max_retries, backoff_factor=0, backoff_jitter=1, respect_retry_after_header=True),
            "fixed": Retry(total=max_retries, backoff_factor=0, backoff_jitter=0, respect_retry_after_header=True),
        }.get(self.retry_strategy)

        return RetryTransport(retry=retry, transport=base_transport)

    async def __aenter__(self) -> WebtoonHttpClient:
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *_: tuple) -> None:
        await self._client.__aexit__()

    async def get(self, url: str) -> httpx.Response:
        if WebtoonMobileURL in url.lower():
            return await self._client.get(url, headers={**self._client.headers, "user-agent": self._get_mobile_ua()})
        return await self._client.get(url)

    @asynccontextmanager
    async def stream(self, method: str, url: str) -> AsyncGenerator[httpx.Response]:
        async with self._client.stream(
            method,
            url,
            headers={
                "referer": WebtoonURL,
                **self._generate_headers(),
            },
        ) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPError as exc:
                if response.status_code == 429:
                    raise ImageDownloadError(
                        url=url, cause=RateLimitedError(f"Rate limitied while downloading image from {url}")
                    ) from exc

            yield response

    def _get_mobile_ua(self) -> str:
        """Returns a randomly chosen user agent for mobile devices"""
        return random.choice(MOBILE_USER_AGENTS)

    def _generate_headers(self) -> dict[str, str]:
        """
        Generates HTTP headers for the webtoon client, including a randomly chosen user agent.
        """
        return {
            "accept-language": "en-US,en;q=0.9",
            "dnt": "1",
            "user-agent": random.choice(USER_AGENTS),
        }
