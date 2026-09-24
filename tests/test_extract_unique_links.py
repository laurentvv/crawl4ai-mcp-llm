from crawl4ai_mcp_llm.crawler import _extract_unique_links


class MockCrawlResult:
    def __init__(self, links=None, has_links_attr=True):
        if has_links_attr:
            self.links = links


def test_extract_unique_links_basic():
    results = [
        MockCrawlResult(
            links={
                "internal": [{"href": "https://example.com/a", "text": "A"}],
                "external": [{"href": "https://google.com", "text": "Google"}],
            }
        ),
        MockCrawlResult(
            links={
                "internal": [{"href": "https://example.com/b", "text": "B"}],
                "external": [{"href": "https://github.com", "text": "GitHub"}],
            }
        ),
    ]

    extracted = _extract_unique_links(results)

    assert [link["href"] for link in extracted["internal"]] == ["https://example.com/a", "https://example.com/b"]
    assert [link["href"] for link in extracted["external"]] == ["https://google.com", "https://github.com"]


def test_extract_unique_links_deduplication_keeps_first():
    results = [
        MockCrawlResult(links={"internal": [{"href": "https://example.com/a", "text": "A1"}]}),
        MockCrawlResult(links={"internal": [{"href": "https://example.com/a", "text": "A2"}]}),
    ]

    extracted = _extract_unique_links(results)

    assert extracted["internal"] == [{"href": "https://example.com/a", "text": "A1"}]


def test_extract_unique_links_missing_attr_or_not_dict():
    results = [
        MockCrawlResult(has_links_attr=False),
        MockCrawlResult(links=["not", "a", "dict"]),
        MockCrawlResult(links={"internal": [{"href": "https://example.com/a"}]}),
    ]

    extracted = _extract_unique_links(results)

    assert extracted["internal"] == [{"href": "https://example.com/a"}]


def test_extract_unique_links_empty_input():
    assert _extract_unique_links([]) == {"internal": [], "external": []}


def test_extract_unique_links_skips_links_without_href():
    extracted = _extract_unique_links([MockCrawlResult(links={"internal": [{"text": "No href"}]})])
    assert extracted["internal"] == []


def test_extract_unique_links_ignores_malformed_entries():
    results = [
        MockCrawlResult(
            links={
                "internal": "not a list",
                "external": ["not a dict", {"href": "https://google.com"}],
            }
        )
    ]

    extracted = _extract_unique_links(results)

    assert extracted == {"internal": [], "external": [{"href": "https://google.com"}]}
