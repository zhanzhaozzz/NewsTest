"""
Playwright 浏览器自动化抓取器

使用无头浏览器渲染页面，适用于需要 JavaScript 渲染的网站
如：微博、抖音、知乎等动态页面
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
import logging
import re

from .base import BaseScraper, ScrapedContent, ScraperResult, ScraperType

logger = logging.getLogger(__name__)


class PlaywrightScraper(BaseScraper):
    """Playwright 浏览器自动化抓取器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.headless = self.config.get('headless', True)
        self.wait_until = self.config.get('wait_until', 'networkidle')
        self.wait_timeout = self.config.get('wait_timeout', 30000)  # 毫秒
        self.viewport = self.config.get('viewport', {'width': 1280, 'height': 720})
        self._browser = None
        self._playwright = None
        
    @property
    def scraper_type(self) -> ScraperType:
        return ScraperType.PLAYWRIGHT
    
    async def _ensure_browser(self):
        """确保浏览器实例已启动"""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless
                )
            except ImportError:
                raise ImportError(
                    "Playwright 未安装。请运行: pip install playwright && playwright install chromium"
                )
    
    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    async def scrape(self, url: str) -> ScraperResult:
        """
        使用 Playwright 抓取内容
        """
        start_time = time.time()
        
        try:
            await self._ensure_browser()
            
            context = await self._browser.new_context(
                viewport=self.viewport,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            try:
                # 导航到页面
                await page.goto(url, wait_until=self.wait_until, timeout=self.wait_timeout)
                
                # 等待一下让动态内容加载
                await page.wait_for_timeout(1000)
                
                # 提取内容
                content = await self._extract_content(page, url)
                
                elapsed = time.time() - start_time
                
                return ScraperResult.success_result(
                    content=content,
                    scraper_type=self.scraper_type,
                    elapsed_time=elapsed
                )
                
            finally:
                await page.close()
                await context.close()
                
        except asyncio.TimeoutError:
            return ScraperResult.failure(
                f"Playwright 页面加载超时 ({self.wait_timeout}ms)",
                self.scraper_type
            )
        except Exception as e:
            logger.exception(f"Playwright 抓取异常: {url}")
            return ScraperResult.failure(
                f"Playwright 抓取失败: {str(e)}",
                self.scraper_type
            )
    
    async def _extract_content(self, page, url: str) -> ScrapedContent:
        """从页面提取内容"""
        
        # 获取标题
        title = await page.title()
        
        # 尝试获取 Open Graph 标题（通常更准确）
        og_title = await page.evaluate('''() => {
            const meta = document.querySelector('meta[property="og:title"]');
            return meta ? meta.content : null;
        }''')
        if og_title:
            title = og_title
        
        # 提取正文内容 - 尝试多种选择器
        content = ""
        
        # 常见的文章内容选择器
        content_selectors = [
            'article',
            '[role="article"]',
            '.article-content',
            '.post-content', 
            '.entry-content',
            '.content-article',
            '#article-content',
            '.news-content',
            '.detail-content',
            'main article',
            '.main-content',
        ]
        
        for selector in content_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if len(content) > 100:  # 至少要有一定内容
                        break
            except Exception:
                continue
        
        # 如果上面的选择器都没找到，尝试获取 body 中的主要文本
        if not content or len(content) < 100:
            content = await page.evaluate('''() => {
                // 移除脚本、样式、导航等
                const elementsToRemove = document.querySelectorAll(
                    'script, style, nav, header, footer, aside, .sidebar, .ads, .advertisement, .comment, .comments'
                );
                elementsToRemove.forEach(el => el.remove());
                
                // 获取 body 文本
                return document.body.innerText;
            }''')
        
        # 清理内容
        content = self._clean_content(content)
        
        # 提取图片
        images = await page.evaluate('''() => {
            const imgs = document.querySelectorAll('article img, .content img, .post img');
            return Array.from(imgs).map(img => img.src).filter(src => src && src.startsWith('http'));
        }''')
        
        # 提取作者（如果有）
        author = await page.evaluate('''() => {
            const authorMeta = document.querySelector('meta[name="author"], meta[property="article:author"]');
            if (authorMeta) return authorMeta.content;
            
            const authorElement = document.querySelector('.author, .byline, [rel="author"]');
            if (authorElement) return authorElement.innerText.trim();
            
            return '';
        }''')
        
        # 提取发布时间
        publish_time = await page.evaluate('''() => {
            const timeMeta = document.querySelector('meta[property="article:published_time"], time[datetime]');
            if (timeMeta) {
                return timeMeta.content || timeMeta.getAttribute('datetime');
            }
            return null;
        }''')
        
        return ScrapedContent(
            url=url,
            title=title or "",
            content=content,
            author=author or "",
            images=images[:10] if images else [],  # 最多保留10张图
            metadata={
                'source': 'playwright',
                'has_og_title': bool(og_title)
            }
        )
    
    def _clean_content(self, content: str) -> str:
        """清理提取的内容"""
        if not content:
            return ""
        
        # 移除多余空行
        lines = content.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            line = line.strip()
            if not line:
                if not prev_empty:
                    cleaned_lines.append('')
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False
        
        content = '\n'.join(cleaned_lines)
        
        # 移除常见的无用内容模式
        patterns_to_remove = [
            r'分享到\s*(微信|微博|QQ|朋友圈)',
            r'点击\s*(关注|订阅|收藏)',
            r'扫码\s*关注',
            r'广告\s*$',
            r'^相关\s*(推荐|阅读|文章)',
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.MULTILINE | re.IGNORECASE)
        
        return self._clean_text(content)
    
    async def scrape_with_wait(
        self, 
        url: str, 
        wait_selector: str = None,
        wait_time: int = 2000
    ) -> ScraperResult:
        """
        抓取内容，等待特定元素或时间
        
        Args:
            url: 要抓取的 URL
            wait_selector: 等待的 CSS 选择器
            wait_time: 额外等待时间（毫秒）
        """
        start_time = time.time()
        
        try:
            await self._ensure_browser()
            
            context = await self._browser.new_context(
                viewport=self.viewport,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until=self.wait_until, timeout=self.wait_timeout)
                
                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=self.wait_timeout)
                
                await page.wait_for_timeout(wait_time)
                
                content = await self._extract_content(page, url)
                elapsed = time.time() - start_time
                
                return ScraperResult.success_result(
                    content=content,
                    scraper_type=self.scraper_type,
                    elapsed_time=elapsed
                )
                
            finally:
                await page.close()
                await context.close()
                
        except Exception as e:
            logger.exception(f"Playwright 抓取异常: {url}")
            return ScraperResult.failure(
                f"Playwright 抓取失败: {str(e)}",
                self.scraper_type
            )
