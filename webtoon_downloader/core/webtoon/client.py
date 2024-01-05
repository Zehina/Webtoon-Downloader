from __future__ import annotations

import random

import httpx

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


def get_mobile_ua() -> str:
    """Returns a randomly chosen user agent for mobile devices"""
    return random.choice(MOBILE_USER_AGENTS)


def _generate_headers() -> dict[str, str]:
    """
    Generates HTTP headers for the webtoon client, including a randomly chosen user agent.
    """
    return {
        "accept-language": "en-US,en;q=0.9",
        "dnt": "1",
        "user-agent": random.choice(USER_AGENTS),
    }


def new() -> httpx.AsyncClient:
    """
    Creates and returns an asynchronous HTTP client configured for scrapping webtoon website.

    The client uses HTTP/2, custom headers with a randomly selected user agent,
    and is configured with high limits for maximum connections and keep-alive connections.
    """
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=200)
    return httpx.AsyncClient(
        limits=limits,
        http2=True,
        headers=_generate_headers(),
        follow_redirects=True,
    )


def new_image_client() -> httpx.AsyncClient:
    """
    Creates and returns an asynchronous HTTP client configured for downloading webtoon images.

    The client uses HTTP/2, custom headers including a referer and a randomly selected user agent,
    and is configured with high limits for maximum connections and keep-alive connections.
    """
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=200)
    return httpx.AsyncClient(
        limits=limits,
        http2=True,
        headers={
            "referer": "https://www.webtoons.com/",
            **_generate_headers(),
        },
    )
