"""
TrendRadar 内容抓取模块

提供多种方式抓取新闻正文内容：
- Jina Reader: 免费 API，将 URL 转为干净文本（优先使用）
- Playwright: 浏览器自动化，处理 JS 渲染页面
- Simple: 轻量爬虫，使用 requests + readability
"""

from .base import BaseScraper, ScrapedContent, ScraperResult
from .jina_reader import JinaReaderScraper
from .playwright_scraper import PlaywrightScraper
from .simple_scraper import SimpleScraper
from .router import ScraperRouter
from .content_store import ContentStore

__all__ = [
    'BaseScraper',
    'ScrapedContent', 
    'ScraperResult',
    'JinaReaderScraper',
    'PlaywrightScraper',
    'SimpleScraper',
    'ScraperRouter',
    'ContentStore',
]
