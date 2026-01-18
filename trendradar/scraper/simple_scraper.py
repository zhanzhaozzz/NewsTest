"""
简单爬虫抓取器

使用 requests + readability 提取网页内容
轻量级方案，适用于静态页面
"""

import time
import asyncio
from typing import Dict, Any, Optional
import logging
import re
from concurrent.futures import ThreadPoolExecutor

from .base import BaseScraper, ScrapedContent, ScraperResult, ScraperType

logger = logging.getLogger(__name__)

# 线程池用于运行同步的 requests
_executor = ThreadPoolExecutor(max_workers=10)


class SimpleScraper(BaseScraper):
    """简单爬虫抓取器 - 使用 requests + readability"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.user_agent = self.config.get(
            'user_agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.verify_ssl = self.config.get('verify_ssl', True)
        
    @property
    def scraper_type(self) -> ScraperType:
        return ScraperType.SIMPLE
    
    async def scrape(self, url: str) -> ScraperResult:
        """
        使用 requests 抓取内容
        """
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                _executor,
                self._sync_scrape,
                url
            )
            return result
        except Exception as e:
            logger.exception(f"Simple 抓取异常: {url}")
            return ScraperResult.failure(
                f"Simple 抓取失败: {str(e)}",
                self.scraper_type
            )
    
    def _sync_scrape(self, url: str) -> ScraperResult:
        """同步抓取方法"""
        import requests
        
        start_time = time.time()
        
        try:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                allow_redirects=True
            )
            
            response.raise_for_status()
            
            # 检测编码
            response.encoding = self._detect_encoding(response)
            html = response.text
            
            # 提取内容
            content = self._extract_content(html, url)
            
            elapsed = time.time() - start_time
            
            return ScraperResult.success_result(
                content=content,
                scraper_type=self.scraper_type,
                elapsed_time=elapsed
            )
            
        except requests.Timeout:
            return ScraperResult.failure(
                f"请求超时 ({self.timeout}秒)",
                self.scraper_type
            )
        except requests.RequestException as e:
            return ScraperResult.failure(
                f"请求失败: {str(e)}",
                self.scraper_type
            )
        except Exception as e:
            return ScraperResult.failure(
                f"抓取失败: {str(e)}",
                self.scraper_type
            )
    
    def _detect_encoding(self, response) -> str:
        """检测响应编码"""
        # 首先尝试从 Content-Type 获取
        content_type = response.headers.get('Content-Type', '')
        if 'charset=' in content_type:
            charset = content_type.split('charset=')[-1].split(';')[0].strip()
            return charset
        
        # 尝试从 HTML meta 标签获取
        content = response.content[:1024]
        
        # 检查 meta charset
        charset_match = re.search(b'charset=["\']?([^"\'>\s]+)', content, re.IGNORECASE)
        if charset_match:
            return charset_match.group(1).decode('ascii', errors='ignore')
        
        # 默认使用 UTF-8
        return 'utf-8'
    
    def _extract_content(self, html: str, url: str) -> ScrapedContent:
        """从 HTML 提取内容"""
        
        title = ""
        content = ""
        author = ""
        images = []
        
        try:
            # 尝试使用 readability-lxml
            from readability import Document
            doc = Document(html)
            title = doc.title()
            content_html = doc.summary()
            
            # 从提取的 HTML 中获取纯文本
            content = self._html_to_text(content_html)
            
        except ImportError:
            logger.warning("readability-lxml 未安装，使用简单提取")
            # 回退到简单提取
            title, content = self._simple_extract(html)
        except Exception as e:
            logger.warning(f"readability 提取失败，使用简单提取: {e}")
            title, content = self._simple_extract(html)
        
        # 提取作者和图片（使用简单正则）
        author = self._extract_author(html)
        images = self._extract_images(html, url)
        
        return ScrapedContent(
            url=url,
            title=title,
            content=self._clean_text(content),
            html_content=html[:10000] if len(html) > 10000 else html,  # 保留部分原始 HTML
            author=author,
            images=images[:10],
            metadata={'source': 'simple'}
        )
    
    def _html_to_text(self, html: str) -> str:
        """将 HTML 转换为纯文本"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # 移除脚本和样式
            for element in soup(['script', 'style', 'nav', 'footer', 'aside']):
                element.decompose()
            
            text = soup.get_text(separator='\n')
            return text
            
        except ImportError:
            # 简单的正则替换
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'&[a-z]+;', ' ', text)
            return text
    
    def _simple_extract(self, html: str) -> tuple:
        """简单提取标题和内容"""
        
        # 提取标题
        title = ""
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        
        # 移除脚本和样式
        content = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<nav[^>]*>.*?</nav>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<header[^>]*>.*?</header>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<footer[^>]*>.*?</footer>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # 尝试提取文章主体
        article_match = re.search(r'<article[^>]*>(.*?)</article>', content, flags=re.DOTALL | re.IGNORECASE)
        if article_match:
            content = article_match.group(1)
        else:
            # 尝试提取 main
            main_match = re.search(r'<main[^>]*>(.*?)</main>', content, flags=re.DOTALL | re.IGNORECASE)
            if main_match:
                content = main_match.group(1)
        
        # 移除所有标签
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'&nbsp;', ' ', content)
        content = re.sub(r'&[a-z]+;', ' ', content)
        
        return title, content
    
    def _extract_author(self, html: str) -> str:
        """提取作者"""
        # 尝试从 meta 标签获取
        author_match = re.search(r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if author_match:
            return author_match.group(1).strip()
        
        # 尝试另一种格式
        author_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']author["\']', html, re.IGNORECASE)
        if author_match:
            return author_match.group(1).strip()
        
        return ""
    
    def _extract_images(self, html: str, base_url: str) -> list:
        """提取图片 URL"""
        from urllib.parse import urljoin
        
        images = []
        
        # 提取 img 标签的 src
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        matches = re.findall(img_pattern, html, re.IGNORECASE)
        
        for src in matches:
            # 跳过小图标和 data URI
            if 'data:' in src or '.ico' in src or 'icon' in src.lower():
                continue
            
            # 转换为绝对 URL
            full_url = urljoin(base_url, src)
            
            if full_url.startswith('http'):
                images.append(full_url)
        
        return images
