"""Hardened browser and crawler configuration for Crawl4AI (SEC-013, Q8, §28)."""

from crawl4ai import BrowserConfig, CrawlerRunConfig

CHROMIUM_HARDENING_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--no-first-run",
    "--no-zygote",
]


def get_browser_config() -> BrowserConfig:
    """Return secure, server-side BrowserConfig for Crawl4AI with sandbox and memory optimizations."""
    return BrowserConfig(
        headless=True,
        extra_args=CHROMIUM_HARDENING_ARGS,
        verbose=False,
    )


def get_crawler_run_config(timeout_seconds: int = 45) -> CrawlerRunConfig:
    """Return run configuration with explicit page timeouts and extraction parameters."""
    return CrawlerRunConfig(
        page_timeout=timeout_seconds * 1000,
        word_count_threshold=1,
        remove_overlay_elements=True,
    )
