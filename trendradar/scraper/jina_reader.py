"""
Jina Reader 内容抓取器

使用 Jina AI 的免费 Reader API 将网页转换为干净的 Markdown/文本
API 文档: https://jina.ai/reader/
免费额度: 1M tokens/月
"""

import time
import asyncio
from typing import Dict, Any, Optional
import logging

from .base import BaseScraper, ScrapedContent, ScraperResult, ScraperType

logger = logging.getLogger(__name__)


class JinaReaderScraper(BaseScraper):
    """Jina Reader 抓取器 - 免费 API，推荐优先使用"""
    
    DEFAULT_API_URL = "https://r.jina.ai/"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.api_url = self.config.get('api_url', self.DEFAULT_API_URL)
        self.api_key = self.config.get('api_key', '')  # 可选的 API Key
        self.return_format = self.config.get('return_format', 'text')  # text 或 markdown
        
    @property
    def scraper_type(self) -> ScraperType:
        return ScraperType.JINA_READER
    
    async def scrape(self, url: str) -> ScraperResult:
        """
        使用 Jina Reader API 抓取内容
        
        Jina Reader 会：
        1. 访问网页并渲染 JavaScript
        2. 提取主要内容，过滤广告和导航
        3. 返回干净的文本或 Markdown
        """
        import aiohttp
        
        start_time = time.time()
        
        try:
            # Jina Reader 的使用方式：直接在 URL 前加上 API 地址
            reader_url = f"{self.api_url}{url}"
            
            headers = {
                'Accept': 'text/plain',
                'User-Agent': 'TrendRadar/1.0'
            }
            
            # 如果有 API Key，添加到 Header
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            # 添加额外参数
            if self.return_format == 'markdown':
                headers['X-Return-Format'] = 'markdown'
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(reader_url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return ScraperResult.failure(
                            f"Jina Reader API 返回错误 {response.status}: {error_text[:200]}",
                            self.scraper_type
                        )
                    
                    content_text = await response.text()
            
            # 解析返回的内容
            parsed = self._parse_jina_response(content_text, url)
            
            elapsed = time.time() - start_time
            
            return ScraperResult.success_result(
                content=parsed,
                scraper_type=self.scraper_type,
                elapsed_time=elapsed
            )
            
        except asyncio.TimeoutError:
            return ScraperResult.failure(
                f"Jina Reader 请求超时 ({self.timeout}秒)",
                self.scraper_type
            )
        except aiohttp.ClientError as e:
            return ScraperResult.failure(
                f"Jina Reader 网络错误: {str(e)}",
                self.scraper_type
            )
        except Exception as e:
            logger.exception(f"Jina Reader 抓取异常: {url}")
            return ScraperResult.failure(
                f"Jina Reader 抓取失败: {str(e)}",
                self.scraper_type
            )
    
    def _parse_jina_response(self, content: str, url: str) -> ScrapedContent:
        """
        解析 Jina Reader 返回的内容
        
        Jina Reader 返回格式通常是：
        Title: 文章标题
        URL Source: 原始URL
        
        正文内容...
        """
        title = ""
        main_content = content
        
        lines = content.split('\n')
        content_start = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 提取标题
            if line_stripped.startswith('Title:'):
                title = line_stripped[6:].strip()
                content_start = i + 1
                continue
            
            # 跳过 URL Source 行
            if line_stripped.startswith('URL Source:'):
                content_start = i + 1
                continue
            
            # 跳过 Markdown Content 标记
            if line_stripped.startswith('Markdown Content:'):
                content_start = i + 1
                continue
            
            # 遇到非元数据行，开始正文
            if line_stripped and not line_stripped.startswith(('Title:', 'URL Source:', 'Markdown Content:')):
                content_start = i
                break
        
        # 提取正文
        main_content = '\n'.join(lines[content_start:])
        main_content = self._clean_text(main_content)
        
        return ScrapedContent(
            url=url,
            title=title,
            content=main_content,
            metadata={
                'source': 'jina_reader',
                'format': self.return_format
            }
        )
    
    async def scrape_with_options(
        self, 
        url: str,
        no_cache: bool = False,
        target_selector: str = None,
        wait_for_selector: str = None,
        remove_selector: str = None
    ) -> ScraperResult:
        """
        使用高级选项抓取内容
        
        Args:
            url: 要抓取的 URL
            no_cache: 是否禁用缓存
            target_selector: CSS 选择器，只提取匹配的元素
            wait_for_selector: 等待特定元素出现后再提取
            remove_selector: 移除匹配的元素
        """
        import aiohttp
        
        start_time = time.time()
        
        try:
            reader_url = f"{self.api_url}{url}"
            
            headers = {
                'Accept': 'text/plain',
                'User-Agent': 'TrendRadar/1.0'
            }
            
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            if no_cache:
                headers['X-No-Cache'] = 'true'
            
            if target_selector:
                headers['X-Target-Selector'] = target_selector
            
            if wait_for_selector:
                headers['X-Wait-For-Selector'] = wait_for_selector
                
            if remove_selector:
                headers['X-Remove-Selector'] = remove_selector
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(reader_url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return ScraperResult.failure(
                            f"Jina Reader API 返回错误 {response.status}: {error_text[:200]}",
                            self.scraper_type
                        )
                    
                    content_text = await response.text()
            
            parsed = self._parse_jina_response(content_text, url)
            elapsed = time.time() - start_time
            
            return ScraperResult.success_result(
                content=parsed,
                scraper_type=self.scraper_type,
                elapsed_time=elapsed
            )
            
        except Exception as e:
            logger.exception(f"Jina Reader 高级抓取异常: {url}")
            return ScraperResult.failure(
                f"Jina Reader 抓取失败: {str(e)}",
                self.scraper_type
            )
