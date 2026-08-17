"""Facebook Ads Intelligence & Campaign Management MCP Server."""

import os
import pathlib

# Ensure Crawl4AI has a guaranteed writable base directory before crawl4ai imports (SEC-044)
if "CRAWL4_AI_BASE_DIRECTORY" not in os.environ:
    _local_crawl_dir = pathlib.Path(__file__).parent.parent / ".scratch" / "crawl4ai"
    try:
        _local_crawl_dir.mkdir(parents=True, exist_ok=True)
        os.environ["CRAWL4_AI_BASE_DIRECTORY"] = str(_local_crawl_dir)
    except OSError:
        os.environ["CRAWL4_AI_BASE_DIRECTORY"] = "/tmp"

__version__ = "3.0.0"
