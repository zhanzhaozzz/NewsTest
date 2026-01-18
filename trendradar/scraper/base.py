"""
内容抓取器基类

定义抓取器的通用接口和数据结构
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class ScraperType(Enum):
    """抓取器类型"""
    JINA_READER = "jina_reader"
    PLAYWRIGHT = "playwright"
    SIMPLE = "simple"


@dataclass
class ScrapedContent:
    """抓取到的内容"""
    url: str                           # 原始 URL
    title: str = ""                    # 文章标题
    content: str = ""                  # 正文内容（纯文本）
    html_content: str = ""             # 原始 HTML（可选）
    author: str = ""                   # 作者
    publish_time: Optional[datetime] = None  # 发布时间
    word_count: int = 0                # 字数统计
    images: List[str] = field(default_factory=list)  # 图片列表
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    
    def __post_init__(self):
        """计算字数"""
        if self.content and self.word_count == 0:
            self.word_count = len(self.content)


@dataclass 
class ScraperResult:
    """抓取结果"""
    success: bool                      # 是否成功
    content: Optional[ScrapedContent] = None  # 抓取到的内容
    error: str = ""                    # 错误信息
    scraper_type: ScraperType = ScraperType.SIMPLE  # 使用的抓取器类型
    elapsed_time: float = 0.0          # 耗时（秒）
    
    @classmethod
    def failure(cls, error: str, scraper_type: ScraperType = ScraperType.SIMPLE) -> 'ScraperResult':
        """创建失败结果"""
        return cls(success=False, error=error, scraper_type=scraper_type)
    
    @classmethod
    def success_result(cls, content: ScrapedContent, scraper_type: ScraperType, elapsed_time: float = 0.0) -> 'ScraperResult':
        """创建成功结果"""
        return cls(success=True, content=content, scraper_type=scraper_type, elapsed_time=elapsed_time)


class BaseScraper(ABC):
    """抓取器基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化抓取器
        
        Args:
            config: 抓取器配置
        """
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30)
        self.enabled = self.config.get('enabled', True)
    
    @property
    @abstractmethod
    def scraper_type(self) -> ScraperType:
        """返回抓取器类型"""
        pass
    
    @abstractmethod
    async def scrape(self, url: str) -> ScraperResult:
        """
        抓取指定 URL 的内容
        
        Args:
            url: 要抓取的 URL
            
        Returns:
            ScraperResult: 抓取结果
        """
        pass
    
    async def scrape_batch(self, urls: List[str], max_concurrent: int = 5) -> List[ScraperResult]:
        """
        批量抓取多个 URL
        
        Args:
            urls: URL 列表
            max_concurrent: 最大并发数
            
        Returns:
            List[ScraperResult]: 抓取结果列表
        """
        import asyncio
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> ScraperResult:
            async with semaphore:
                return await self.scrape(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    def is_enabled(self) -> bool:
        """检查抓取器是否启用"""
        return self.enabled
    
    def _clean_text(self, text: str) -> str:
        """清理文本，去除多余空白"""
        if not text:
            return ""
        
        import re
        # 替换多个连续空白为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空白
        text = text.strip()
        return text
    
    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""
