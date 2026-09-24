import re
from datetime import datetime
from unittest.mock import patch

import pytest

from crawl4ai_mcp_llm.utils import generate_filename_from_url


@pytest.fixture
def frozen_now():
    with patch("crawl4ai_mcp_llm.utils.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2023, 10, 27, 14, 30, 0)
        yield


@pytest.mark.parametrize(
    ("url", "host_part"),
    [
        ("https://example.com/some/path", "example_com"),
        ("https://a.b.c.example.org/test", "a_b_c_example_org"),
        ("http://localhost:8080/api/data", "localhost_8080"),
        ("example.com", "example_com"),
        ("https://user:pass@example.com/", "example_com"),
    ],
)
def test_filename_from_url(frozen_now, url, host_part):
    name = generate_filename_from_url(url)
    assert re.fullmatch(rf"crawl_{host_part}_20231027_143000_[0-9a-f]{{6}}\.md", name)


def test_filename_is_portable(frozen_now):
    name = generate_filename_from_url("http://[::1]:8080/")
    assert re.fullmatch(r"[\w.-]+", name)


def test_filenames_are_unique_within_the_same_second(frozen_now):
    assert generate_filename_from_url("https://example.com") != generate_filename_from_url("https://example.com")
