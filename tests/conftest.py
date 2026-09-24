import pytest

from crawl4ai_mcp_llm import security
from crawl4ai_mcp_llm.config import ALLOW_JS_ENV, ALLOW_PRIVATE_NETWORKS_ENV, RESULTS_DIR_ENV

PUBLIC_TEST_IP = "93.184.215.14"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def results_dir(tmp_path):
    return tmp_path / "results"


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, results_dir):
    """Keep tests off the network, the home directory and the caller's env."""
    monkeypatch.setenv(RESULTS_DIR_ENV, str(results_dir))
    monkeypatch.delenv(ALLOW_JS_ENV, raising=False)
    monkeypatch.delenv(ALLOW_PRIVATE_NETWORKS_ENV, raising=False)

    async def fake_resolve_host(hostname):
        return [PUBLIC_TEST_IP]

    monkeypatch.setattr(security, "resolve_host", fake_resolve_host)


class FakeStrategy:
    def __init__(self):
        self.killed_sessions = []

    async def kill_session(self, session_id):
        self.killed_sessions.append(session_id)


class FakeCrawler:
    """Async context manager standing in for crawl4ai's AsyncWebCrawler."""

    def __init__(self, results=None, error=None):
        self.results = results if results is not None else []
        self.error = error
        self.calls = []
        self.started = 0
        self.closed = 0
        self.crawler_strategy = FakeStrategy()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def start(self):
        self.started += 1

    async def close(self):
        self.closed += 1

    async def arun(self, url, config=None, **kwargs):
        self.calls.append((url, config))
        if self.error:
            raise self.error
        return self.results


@pytest.fixture
def fake_crawler(monkeypatch):
    crawler = FakeCrawler()
    monkeypatch.setattr("crawl4ai_mcp_llm.crawler.AsyncWebCrawler", lambda *a, **kw: crawler)
    return crawler
