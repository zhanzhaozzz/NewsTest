"""
智能抓取路由器

根据 URL 域名和配置自动选择最佳的抓取方式
优先级: Jina Reader > Simple > Playwright
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging
from urllib.parse import urlparse

from .base import BaseScraper, ScraperResult, ScraperType
from .jina_reader import JinaReaderScraper
from .playwright_scraper import PlaywrightScraper
from .simple_scraper import SimpleScraper

logger = logging.getLogger(__name__)


class ScraperRouter:
    """
    智能抓取路由器
    
    根据域名规则和抓取器状态自动选择最佳抓取方式
    支持失败重试和降级策略
    """
    
    # 默认需要使用 Playwright 的域名（需要 JS 渲染）
    JS_RENDER_DOMAINS = {
        'weibo.com',
        'weibo.cn',
        'm.weibo.cn',
        'douyin.com',
        'www.douyin.com',
        'twitter.com',
        'x.com',
        'instagram.com',
        'facebook.com',
        'tiktok.com',
    }
    
    # 推荐使用 Jina Reader 的域名
    JINA_PREFERRED_DOMAINS = {
        'zhihu.com',
        'www.zhihu.com',
        'zhuanlan.zhihu.com',
        'mp.weixin.qq.com',
        '36kr.com',
        'www.36kr.com',
        'ithome.com',
        'www.ithome.com',
        'baidu.com',
        'news.baidu.com',
        'finance.sina.com.cn',
        'tech.sina.com.cn',
        'news.sina.com.cn',
        'sohu.com',
        'www.sohu.com',
        'qq.com',
        'news.qq.com',
        'thepaper.cn',
        'www.thepaper.cn',
        'jiemian.com',
        'www.jiemian.com',
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化路由器
        
        Args:
            config: 配置字典，包含各抓取器的配置
        """
        self.config = config or {}
        
        # 初始化抓取器
        self.scrapers: Dict[ScraperType, BaseScraper] = {}
        
        jina_config = self.config.get('methods', {}).get('jina_reader', {})
        if jina_config.get('enabled', True):
            self.scrapers[ScraperType.JINA_READER] = JinaReaderScraper(jina_config)
        
        simple_config = self.config.get('methods', {}).get('simple', {})
        if simple_config.get('enabled', True):
            self.scrapers[ScraperType.SIMPLE] = SimpleScraper(simple_config)
        
        playwright_config = self.config.get('methods', {}).get('playwright', {})
        if playwright_config.get('enabled', True):
            self.scrapers[ScraperType.PLAYWRIGHT] = PlaywrightScraper(playwright_config)
        
        # 加载自定义域名规则
        self.domain_rules: Dict[str, str] = self.config.get('domain_rules', {})
        
        # 是否启用内容抓取
        self.enabled = self.config.get('enabled', True)
        
        # Top N 配置
        self.top_n = self.config.get('top_n', 20)
        
        # 重试配置
        self.max_retries = self.config.get('max_retries', 2)
        
    async def scrape(self, url: str) -> ScraperResult:
        """
        智能抓取 URL 内容
        
        抓取策略:
        1. 根据域名规则选择首选抓取器
        2. 如果首选失败，尝试其他抓取器
        3. 返回第一个成功的结果
        """
        if not self.enabled:
            return ScraperResult.failure("内容抓取已禁用", ScraperType.SIMPLE)
        
        if not self.scrapers:
            return ScraperResult.failure("没有可用的抓取器", ScraperType.SIMPLE)
        
        # 确定抓取器优先级
        priority_order = self._get_scraper_priority(url)
        
        last_error = ""
        
        for scraper_type in priority_order:
            if scraper_type not in self.scrapers:
                continue
            
            scraper = self.scrapers[scraper_type]
            
            logger.debug(f"尝试使用 {scraper_type.value} 抓取: {url}")
            
            result = await scraper.scrape(url)
            
            if result.success:
                logger.info(f"抓取成功 [{scraper_type.value}]: {url}")
                return result
            
            last_error = result.error
            logger.warning(f"抓取失败 [{scraper_type.value}]: {result.error}")
        
        return ScraperResult.failure(f"所有抓取器均失败: {last_error}", ScraperType.SIMPLE)
    
    async def scrape_batch(
        self, 
        urls: List[str], 
        max_concurrent: int = 5,
        progress_callback: callable = None
    ) -> Dict[str, ScraperResult]:
        """
        批量抓取多个 URL
        
        Args:
            urls: URL 列表
            max_concurrent: 最大并发数
            progress_callback: 进度回调函数 (completed, total)
            
        Returns:
            Dict[str, ScraperResult]: URL -> 抓取结果 的映射
        """
        if not urls:
            return {}
        
        # 限制到 Top N
        urls_to_scrape = urls[:self.top_n]
        
        results: Dict[str, ScraperResult] = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0
        
        async def scrape_with_semaphore(url: str) -> tuple:
            nonlocal completed
            async with semaphore:
                result = await self.scrape(url)
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(urls_to_scrape))
                return url, result
        
        tasks = [scrape_with_semaphore(url) for url in urls_to_scrape]
        
        for coro in asyncio.as_completed(tasks):
            url, result = await coro
            results[url] = result
        
        return results
    
    def _get_scraper_priority(self, url: str) -> List[ScraperType]:
        """
        获取 URL 的抓取器优先级列表
        """
        domain = self._extract_domain(url)
        
        # 1. 检查自定义域名规则
        if domain in self.domain_rules:
            rule = self.domain_rules[domain]
            primary = ScraperType(rule)
            return self._build_priority_list(primary)
        
        # 2. 检查是否需要 JS 渲染
        for js_domain in self.JS_RENDER_DOMAINS:
            if domain.endswith(js_domain) or domain == js_domain:
                return self._build_priority_list(ScraperType.PLAYWRIGHT)
        
        # 3. 检查是否推荐使用 Jina
        for jina_domain in self.JINA_PREFERRED_DOMAINS:
            if domain.endswith(jina_domain) or domain == jina_domain:
                return self._build_priority_list(ScraperType.JINA_READER)
        
        # 4. 默认优先级: Jina > Simple > Playwright
        return [ScraperType.JINA_READER, ScraperType.SIMPLE, ScraperType.PLAYWRIGHT]
    
    def _build_priority_list(self, primary: ScraperType) -> List[ScraperType]:
        """构建优先级列表，将指定的抓取器放在首位"""
        all_types = [ScraperType.JINA_READER, ScraperType.SIMPLE, ScraperType.PLAYWRIGHT]
        result = [primary]
        for t in all_types:
            if t != primary:
                result.append(t)
        return result
    
    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""
    
    async def close(self):
        """关闭所有抓取器"""
        for scraper in self.scrapers.values():
            if hasattr(scraper, 'close'):
                await scraper.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取抓取器状态统计"""
        return {
            'enabled': self.enabled,
            'top_n': self.top_n,
            'available_scrapers': [t.value for t in self.scrapers.keys()],
            'custom_domain_rules': len(self.domain_rules),
        }
