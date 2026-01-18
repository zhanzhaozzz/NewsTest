"""
AI 分析器

使用 LLM 对新闻进行智能分析
"""

import json
import re
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .client import LLMClient, ChatMessage
from .prompts import PromptManager

logger = logging.getLogger(__name__)


@dataclass
class CategoryResult:
    """分类结果"""
    news_id: str
    primary_category: str
    secondary_category: Optional[str] = None
    confidence: int = 0
    reason: str = ""


@dataclass
class InsightItem:
    """洞察项"""
    domain: str  # 领域
    content: str  # 洞察内容
    importance: int = 0  # 重要性 1-5


@dataclass
class NewsSummary:
    """新闻摘要"""
    news_id: str
    title: str
    summary: str
    category: str = ""


@dataclass
class AnalysisResult:
    """分析结果"""
    success: bool
    
    # 每日简报
    daily_briefing: str = ""
    
    # 分类结果
    categories: List[CategoryResult] = field(default_factory=list)
    
    # 洞察列表
    insights: List[InsightItem] = field(default_factory=list)
    
    # 新闻摘要
    summaries: List[NewsSummary] = field(default_factory=list)
    
    # 深度报告
    deep_research: str = ""
    
    # 元数据
    generated_at: str = ""
    model_used: str = ""
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: str = ""
    
    @classmethod
    def failure(cls, error: str) -> 'AnalysisResult':
        return cls(success=False, error=error)


class AIAnalyzer:
    """
    AI 分析器
    
    提供新闻分析功能：
    - 生成每日简报
    - 智能分类
    - 洞察提取
    - 深度研究报告
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化分析器
        
        Args:
            config: LLM 配置
        """
        self.config = config or {}
        self.client = LLMClient(config)
        self.prompt_manager = PromptManager(config)
        
        # 功能开关
        features = config.get('features', {}) if config else {}
        self.enable_briefing = features.get('daily_briefing', True)
        self.enable_category = features.get('smart_category', True)
        self.enable_insight = features.get('key_insight', True)
        self.enable_deep_research = features.get('deep_research', False)
        
        # 分类配置
        self.categories = config.get('categories', []) if config else []
    
    def is_available(self) -> bool:
        """检查分析器是否可用"""
        return self.client.is_available()
    
    async def generate_daily_briefing(
        self,
        news_items: List[Dict[str, Any]],
        date: str = None
    ) -> str:
        """
        生成每日简报
        
        Args:
            news_items: 新闻列表
            date: 日期
            
        Returns:
            str: Markdown 格式的简报
        """
        if not self.is_available():
            logger.warning("LLM 不可用，跳过每日简报生成")
            return ""
        
        if not news_items:
            logger.warning("没有新闻数据，跳过简报生成")
            return ""
        
        try:
            system_prompt, user_prompt = self.prompt_manager.render_daily_briefing(
                news_items=news_items,
                date=date
            )
            
            response = await self.client.chat([
                ChatMessage(role='system', content=system_prompt),
                ChatMessage(role='user', content=user_prompt)
            ])
            
            return response.content
            
        except Exception as e:
            logger.error(f"生成每日简报失败: {e}")
            return ""
    
    async def categorize_news(
        self,
        title: str,
        content: str,
        news_id: str = ""
    ) -> Optional[CategoryResult]:
        """
        对单条新闻进行分类
        
        Args:
            title: 新闻标题
            content: 新闻内容
            news_id: 新闻ID
            
        Returns:
            CategoryResult 或 None
        """
        if not self.is_available() or not self.categories:
            return None
        
        try:
            system_prompt, user_prompt = self.prompt_manager.render_categorize(
                title=title,
                content=content,
                categories=self.categories
            )
            
            response = await self.client.chat(
                [
                    ChatMessage(role='system', content=system_prompt),
                    ChatMessage(role='user', content=user_prompt)
                ],
                temperature=0.3  # 分类任务用低温度
            )
            
            # 解析 JSON 响应
            result = self._parse_json_response(response.content)
            
            if result:
                return CategoryResult(
                    news_id=news_id,
                    primary_category=result.get('primary_category', ''),
                    secondary_category=result.get('secondary_category'),
                    confidence=result.get('confidence', 0),
                    reason=result.get('reason', '')
                )
            
        except Exception as e:
            logger.error(f"分类新闻失败: {e}")
        
        return None
    
    async def categorize_batch(
        self,
        news_items: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[CategoryResult]:
        """
        批量分类新闻
        
        Args:
            news_items: 新闻列表
            max_concurrent: 最大并发数
            
        Returns:
            分类结果列表
        """
        if not self.is_available() or not self.categories:
            return []
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def categorize_single(item: Dict) -> Optional[CategoryResult]:
            async with semaphore:
                return await self.categorize_news(
                    title=item.get('title', ''),
                    content=item.get('content', ''),
                    news_id=item.get('id', str(hash(item.get('title', ''))))
                )
        
        tasks = [categorize_single(item) for item in news_items]
        raw_results = await asyncio.gather(*tasks)
        
        for result in raw_results:
            if result:
                results.append(result)
        
        return results
    
    async def extract_insights(
        self,
        news_items: List[Dict[str, Any]]
    ) -> List[InsightItem]:
        """
        提取核心洞察
        
        Args:
            news_items: 新闻列表
            
        Returns:
            洞察列表
        """
        if not self.is_available():
            return []
        
        if not news_items:
            return []
        
        try:
            system_prompt, user_prompt = self.prompt_manager.render_insights(news_items)
            
            response = await self.client.chat([
                ChatMessage(role='system', content=system_prompt),
                ChatMessage(role='user', content=user_prompt)
            ])
            
            # 解析洞察
            return self._parse_insights(response.content)
            
        except Exception as e:
            logger.error(f"提取洞察失败: {e}")
            return []
    
    async def summarize_news(
        self,
        title: str,
        content: str,
        news_id: str = ""
    ) -> Optional[NewsSummary]:
        """
        生成新闻摘要
        
        Args:
            title: 新闻标题
            content: 新闻内容
            news_id: 新闻ID
            
        Returns:
            NewsSummary 或 None
        """
        if not self.is_available():
            return None
        
        try:
            system_prompt, user_prompt = self.prompt_manager.render_summarize(
                title=title,
                content=content
            )
            
            response = await self.client.chat(
                [
                    ChatMessage(role='system', content=system_prompt),
                    ChatMessage(role='user', content=user_prompt)
                ],
                max_tokens=200
            )
            
            return NewsSummary(
                news_id=news_id,
                title=title,
                summary=response.content.strip()
            )
            
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return None
    
    async def generate_deep_research(
        self,
        topic: str,
        news_items: List[Dict[str, Any]],
        date: str = None
    ) -> str:
        """
        生成深度研究报告
        
        Args:
            topic: 研究主题
            news_items: 相关新闻
            date: 日期
            
        Returns:
            Markdown 格式的研究报告
        """
        if not self.is_available():
            return ""
        
        if not news_items:
            return ""
        
        try:
            system_prompt, user_prompt = self.prompt_manager.render_deep_research(
                topic=topic,
                news_items=news_items,
                date=date
            )
            
            response = await self.client.chat(
                [
                    ChatMessage(role='system', content=system_prompt),
                    ChatMessage(role='user', content=user_prompt)
                ],
                max_tokens=8000,
                temperature=0.5
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"生成深度研究报告失败: {e}")
            return ""
    
    async def analyze_full(
        self,
        news_items: List[Dict[str, Any]],
        date: str = None
    ) -> AnalysisResult:
        """
        执行完整的 AI 分析
        
        Args:
            news_items: 新闻列表
            date: 日期
            
        Returns:
            AnalysisResult: 完整分析结果
        """
        if not self.is_available():
            return AnalysisResult.failure("LLM 客户端不可用")
        
        if not news_items:
            return AnalysisResult.failure("没有新闻数据")
        
        result = AnalysisResult(
            success=True,
            generated_at=datetime.now().isoformat(),
            model_used=self.client.model_name
        )
        
        try:
            # 并行执行各项分析
            tasks = []
            
            if self.enable_briefing:
                tasks.append(('briefing', self.generate_daily_briefing(news_items, date)))
            
            if self.enable_insight:
                tasks.append(('insights', self.extract_insights(news_items)))
            
            if self.enable_category:
                tasks.append(('categories', self.categorize_batch(news_items[:10])))  # 只分类前10条
            
            # 等待所有任务完成
            for name, coro in tasks:
                try:
                    value = await coro
                    if name == 'briefing':
                        result.daily_briefing = value
                    elif name == 'insights':
                        result.insights = value
                    elif name == 'categories':
                        result.categories = value
                except Exception as e:
                    logger.error(f"分析任务 {name} 失败: {e}")
            
        except Exception as e:
            logger.error(f"完整分析失败: {e}")
            result.success = False
            result.error = str(e)
        
        return result
    
    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """解析 JSON 响应"""
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _parse_insights(self, text: str) -> List[InsightItem]:
        """解析洞察文本"""
        insights = []
        
        # 匹配格式: "1. [领域] 内容" 或 "- [领域] 内容"
        pattern = r'(?:\d+\.\s*|\-\s*)\[([^\]]+)\]\s*(.+?)(?=(?:\d+\.\s*|\-\s*)\[|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for domain, content in matches:
            insights.append(InsightItem(
                domain=domain.strip(),
                content=content.strip()
            ))
        
        # 如果上面的格式没匹配到，尝试简单的列表格式
        if not insights:
            lines = text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or re.match(r'\d+\.', line)):
                    # 移除前缀
                    content = re.sub(r'^[\d\.\-•\s]+', '', line).strip()
                    if content:
                        insights.append(InsightItem(
                            domain='综合',
                            content=content
                        ))
        
        return insights[:5]  # 最多返回5条
    
    def get_stats(self) -> Dict[str, Any]:
        """获取分析器状态"""
        return {
            'available': self.is_available(),
            'features': {
                'daily_briefing': self.enable_briefing,
                'smart_category': self.enable_category,
                'key_insight': self.enable_insight,
                'deep_research': self.enable_deep_research,
            },
            'categories_count': len(self.categories),
            'client': self.client.get_stats()
        }


# ============================================================================
# 热点新闻分析模块（从 TrendRadarRSS 整合）
# ============================================================================

import os
from pathlib import Path
from typing import Callable


@dataclass
class AIAnalysisResult:
    """AI 热点分析结果"""
    summary: str = ""                    # 热点趋势概述
    keyword_analysis: str = ""           # 关键词热度分析
    sentiment: str = ""                  # 情感倾向分析
    cross_platform: str = ""             # 跨平台关联
    impact: str = ""                     # 潜在影响评估
    signals: str = ""                    # 值得关注的信号
    conclusion: str = ""                 # 总结与建议
    raw_response: str = ""               # 原始响应
    success: bool = False                # 是否成功
    error: str = ""                      # 错误信息
    # 新闻数量统计
    total_news: int = 0                  # 总新闻数（热榜+RSS）
    analyzed_news: int = 0               # 实际分析的新闻数
    max_news_limit: int = 0              # 分析上限配置值
    hotlist_count: int = 0               # 热榜新闻数
    rss_count: int = 0                   # RSS 新闻数


class HotspotAnalyzer:
    """
    热点新闻分析器
    
    专门用于分析热榜和 RSS 新闻的热点趋势
    支持 OpenAI、Google Gemini、Azure OpenAI 等兼容接口
    """

    def __init__(self, config: Dict[str, Any], get_time_func: Callable):
        """
        初始化热点分析器
        
        Args:
            config: AI 分析配置
            get_time_func: 获取当前时间的函数
        """
        self.config = config
        self.get_time_func = get_time_func

        # 从配置或环境变量获取 API Key（支持大小写配置键）
        self.api_key = (
            config.get("API_KEY") or 
            config.get("api_key") or 
            os.environ.get("AI_API_KEY", "")
        )
        self.provider = config.get("PROVIDER") or config.get("provider", "openai")
        self.model = config.get("MODEL_NAME") or config.get("model") or config.get("MODEL", "gpt-4o-mini")
        self.base_url = config.get("API_BASE_URL") or config.get("base_url") or config.get("BASE_URL", "")
        self.timeout = config.get("TIMEOUT") or config.get("timeout", 90)
        self.max_news = config.get("MAX_NEWS_FOR_ANALYSIS") or config.get("max_news_for_analysis", 50)
        self.include_rss = config.get("INCLUDE_RSS", config.get("include_rss", True))
        self.push_mode = config.get("PUSH_MODE") or config.get("push_mode", "both")

        # 加载提示词模板
        prompt_file = config.get("PROMPT_FILE") or config.get("prompt_file", "ai_analysis_prompt.txt")
        self.system_prompt, self.user_prompt_template = self._load_prompt_template(prompt_file)

    def _load_prompt_template(self, prompt_file: str) -> tuple:
        """加载提示词模板"""
        # 获取项目根目录（trendradar 的父目录）
        # __file__ 可能是 .py 或 .pyc，使用 resolve() 获取绝对路径
        current_file = Path(__file__).resolve()
        
        # 当前文件: NewsTest/trendradar/llm/analyzer.py
        # parent: NewsTest/trendradar/llm
        # parent.parent: NewsTest/trendradar
        # parent.parent.parent: NewsTest
        project_root = current_file.parent.parent.parent
        config_dir = project_root / "config"
        prompt_path = config_dir / prompt_file

        if not prompt_path.exists():
            print(f"[AI] 提示词文件不存在: {prompt_path}")
            print(f"[AI] 当前文件位置: {current_file}")
            print(f"[AI] 文件父目录: {current_file.parent}")
            print(f"[AI] 文件父父目录: {current_file.parent.parent}")
            print(f"[AI] 项目根目录: {project_root}")
            print(f"[AI] 配置目录: {config_dir}")
            print(f"[AI] 尝试查找的文件: {prompt_path}")
            
            # 尝试其他可能的路径
            alt_path = current_file.parent.parent.parent.parent / "config" / prompt_file
            if alt_path.exists():
                print(f"[AI] 在备用路径找到文件: {alt_path}")
                prompt_path = alt_path
            else:
                return "", ""

        content = prompt_path.read_text(encoding="utf-8")

        # 解析 [system] 和 [user] 部分
        system_prompt = ""
        user_prompt = ""

        if "[system]" in content and "[user]" in content:
            parts = content.split("[user]")
            system_part = parts[0]
            user_part = parts[1] if len(parts) > 1 else ""

            # 提取 system 内容
            if "[system]" in system_part:
                system_prompt = system_part.split("[system]")[1].strip()

            user_prompt = user_part.strip()
        else:
            # 整个文件作为 user prompt
            user_prompt = content

        return system_prompt, user_prompt

    def analyze(
        self,
        stats: List[Dict],
        rss_stats: Optional[List[Dict]] = None,
        report_mode: str = "daily",
        report_type: str = "当日汇总",
        platforms: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
    ) -> AIAnalysisResult:
        """
        执行 AI 分析
        
        Args:
            stats: 热榜统计数据
            rss_stats: RSS 统计数据
            report_mode: 报告模式
            report_type: 报告类型
            platforms: 平台列表
            keywords: 关键词列表
        
        Returns:
            AIAnalysisResult: 分析结果
        """
        if not self.api_key:
            return AIAnalysisResult(
                success=False,
                error="未配置 AI API Key，请在 config.yaml 或环境变量 AI_API_KEY 中设置"
            )

        # 准备新闻内容并获取统计数据
        news_content, hotlist_total, rss_total, analyzed_count = self._prepare_news_content(stats, rss_stats)
        total_news = hotlist_total + rss_total

        if not news_content:
            return AIAnalysisResult(
                success=False,
                error="没有可分析的新闻内容",
                total_news=total_news,
                hotlist_count=hotlist_total,
                rss_count=rss_total,
                analyzed_news=0,
                max_news_limit=self.max_news
            )

        # 构建提示词
        current_time = self.get_time_func().strftime("%Y-%m-%d %H:%M:%S")

        # 提取关键词
        if not keywords:
            keywords = [s.get("word", "") for s in stats if s.get("word")] if stats else []

        # 使用安全的字符串替换，避免模板中其他花括号（如 JSON 示例）被误解析
        user_prompt = self.user_prompt_template
        user_prompt = user_prompt.replace("{report_mode}", report_mode)
        user_prompt = user_prompt.replace("{report_type}", report_type)
        user_prompt = user_prompt.replace("{current_time}", current_time)
        user_prompt = user_prompt.replace("{news_count}", str(hotlist_total))
        user_prompt = user_prompt.replace("{rss_count}", str(rss_total))
        user_prompt = user_prompt.replace("{platforms}", ", ".join(platforms) if platforms else "多平台")
        user_prompt = user_prompt.replace("{keywords}", ", ".join(keywords[:20]) if keywords else "无")
        user_prompt = user_prompt.replace("{news_content}", news_content)

        # 调用 AI API
        try:
            response = self._call_ai_api(user_prompt)
            result = self._parse_response(response)
            # 填充统计数据
            result.total_news = total_news
            result.hotlist_count = hotlist_total
            result.rss_count = rss_total
            result.analyzed_news = analyzed_count
            result.max_news_limit = self.max_news
            return result
        except Exception as e:
            import requests
            error_type = type(e).__name__
            error_msg = str(e)

            # 针对不同错误类型提供更友好的提示
            if isinstance(e, requests.exceptions.Timeout):
                friendly_msg = f"AI API 请求超时（{self.timeout}秒），请检查网络或增加超时时间"
            elif isinstance(e, requests.exceptions.ConnectionError):
                friendly_msg = f"无法连接到 AI API ({self.base_url or self.provider})，请检查网络和 API 地址"
            elif isinstance(e, requests.exceptions.HTTPError):
                status_code = e.response.status_code if hasattr(e, 'response') and e.response else "未知"
                if status_code == 401:
                    friendly_msg = "AI API 认证失败，请检查 API Key 是否正确"
                elif status_code == 429:
                    friendly_msg = "AI API 请求频率过高，请稍后重试"
                elif status_code == 500:
                    friendly_msg = "AI API 服务器内部错误，请稍后重试"
                else:
                    friendly_msg = f"AI API 返回错误 (HTTP {status_code}): {error_msg[:100]}"
            else:
                # 截断过长的错误消息
                if len(error_msg) > 150:
                    error_msg = error_msg[:150] + "..."
                friendly_msg = f"AI 分析失败 ({error_type}): {error_msg}"

            return AIAnalysisResult(
                success=False,
                error=friendly_msg
            )

    def _prepare_news_content(
        self,
        stats: List[Dict],
        rss_stats: Optional[List[Dict]] = None,
    ) -> tuple:
        """
        准备新闻内容文本（增强版）
        
        热榜新闻包含：来源、标题、排名范围、时间范围、出现次数
        RSS 包含：来源、标题、发布时间
        
        Returns:
            tuple: (content_str, hotlist_total, rss_total, analyzed_count)
        """
        lines = []
        count = 0

        # 计算总新闻数
        hotlist_total = sum(len(s.get("titles", [])) for s in stats) if stats else 0
        rss_total = sum(len(s.get("titles", [])) for s in rss_stats) if rss_stats else 0

        # 热榜内容
        if stats:
            lines.append("### 热榜新闻")
            lines.append("格式: [来源] 标题 | 排名:最高-最低 | 时间:首次~末次 | 出现:N次")
            for stat in stats:
                word = stat.get("word", "")
                titles = stat.get("titles", [])
                if word and titles:
                    lines.append(f"\n**{word}** ({len(titles)}条)")
                    for t in titles:
                        if not isinstance(t, dict):
                            continue
                        title = t.get("title", "")
                        if not title:
                            continue

                        # 来源
                        source = t.get("source_name", t.get("source", ""))

                        # 排名范围
                        ranks = t.get("ranks", [])
                        if ranks:
                            min_rank = min(ranks)
                            max_rank = max(ranks)
                            rank_str = f"{min_rank}" if min_rank == max_rank else f"{min_rank}-{max_rank}"
                        else:
                            rank_str = "-"

                        # 时间范围（简化显示）
                        first_time = t.get("first_time", "")
                        last_time = t.get("last_time", "")
                        time_str = self._format_time_range(first_time, last_time)

                        # 出现次数
                        appear_count = t.get("count", 1)

                        # 构建行：[来源] 标题 | 排名:X-Y | 时间:首次~末次 | 出现:N次
                        if source:
                            line = f"- [{source}] {title}"
                        else:
                            line = f"- {title}"
                        line += f" | 排名:{rank_str} | 时间:{time_str} | 出现:{appear_count}次"
                        lines.append(line)

                        count += 1
                        if count >= self.max_news:
                            break
                if count >= self.max_news:
                    break

        # RSS 内容（仅在启用时提交）
        if self.include_rss and rss_stats and count < self.max_news:
            lines.append("\n### RSS 订阅")
            lines.append("格式: [来源] 标题 | 发布时间")
            for stat in rss_stats:
                word = stat.get("word", "")
                titles = stat.get("titles", [])
                if word and titles:
                    lines.append(f"\n**{word}** ({len(titles)}条)")
                    for t in titles:
                        if not isinstance(t, dict):
                            continue
                        title = t.get("title", "")
                        if not title:
                            continue

                        # 来源
                        source = t.get("source_name", t.get("feed_name", ""))

                        # 发布时间
                        time_display = t.get("time_display", "")

                        # 构建行：[来源] 标题 | 发布时间
                        if source:
                            line = f"- [{source}] {title}"
                        else:
                            line = f"- {title}"
                        if time_display:
                            line += f" | {time_display}"
                        lines.append(line)

                        count += 1
                        if count >= self.max_news:
                            break
                if count >= self.max_news:
                    break

        return "\n".join(lines), hotlist_total, rss_total, count

    def _format_time_range(self, first_time: str, last_time: str) -> str:
        """格式化时间范围（简化显示，只保留时分）"""
        def extract_time(time_str: str) -> str:
            if not time_str:
                return "-"
            # 尝试提取 HH:MM 部分
            # 格式可能是 "2026-01-04 12:30:00" 或 "12:30" 等
            if " " in time_str:
                parts = time_str.split(" ")
                if len(parts) >= 2:
                    time_part = parts[1]
                    if ":" in time_part:
                        return time_part[:5]  # HH:MM
            elif ":" in time_str:
                return time_str[:5]
            return time_str[:5] if len(time_str) >= 5 else time_str

        first = extract_time(first_time)
        last = extract_time(last_time)

        if first == last or last == "-":
            return first
        return f"{first}~{last}"

    def _call_ai_api(self, user_prompt: str) -> str:
        """调用 AI API"""
        if self.provider == "gemini":
            return self._call_gemini(user_prompt)
        return self._call_openai_compatible(user_prompt)

    def _get_api_url(self) -> str:
        """获取完整 API URL"""
        if self.base_url:
            # 如果 base_url 以 /chat/completions 结尾，直接使用
            if self.base_url.endswith("/chat/completions"):
                return self.base_url
            # 否则，自动添加 /chat/completions
            base = self.base_url.rstrip("/")
            return f"{base}/chat/completions"

        # 预设完整端点
        urls = {
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "openai": "https://api.openai.com/v1/chat/completions",
        }
        url = urls.get(self.provider)
        if not url:
            raise ValueError(f"{self.provider} 需要配置 base_url（完整 API 地址）")
        return url

    def _call_openai_compatible(self, user_prompt: str) -> str:
        """调用 OpenAI 兼容接口"""
        import requests

        url = self._get_api_url()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            # 打印详细的错误信息
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = f"\n错误详情: {error_data}"
            except:
                error_detail = f"\n响应内容: {e.response.text[:500]}"
            
            print(f"[AI] API 请求失败:")
            print(f"  - URL: {url}")
            print(f"  - Model: {self.model}")
            print(f"  - System Prompt 长度: {len(self.system_prompt) if self.system_prompt else 0}")
            print(f"  - User Prompt 长度: {len(user_prompt)}")
            print(f"  - 状态码: {e.response.status_code}")
            print(f"  {error_detail}")
            raise

    def _call_gemini(self, user_prompt: str) -> str:
        """调用 Google Gemini API"""
        import requests

        # Gemini API URL 格式: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
        model = self.model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        headers = {
            "Content-Type": "application/json",
        }

        # 构建 Gemini 格式的消息
        contents = []
        if self.system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System instruction: {self.system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood. I will follow these instructions."}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": user_prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2000,
            }
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _parse_response(self, response: str) -> AIAnalysisResult:
        """解析 AI 响应"""
        result = AIAnalysisResult(raw_response=response)

        if not response or not response.strip():
            result.error = "AI 返回空响应"
            return result

        # 尝试解析 JSON
        try:
            # 提取 JSON 部分
            json_str = response

            # 尝试提取 ```json ... ``` 代码块
            if "```json" in response:
                parts = response.split("```json", 1)
                if len(parts) > 1:
                    code_block = parts[1]
                    # 查找结束的 ```
                    end_idx = code_block.find("```")
                    if end_idx != -1:
                        json_str = code_block[:end_idx]
                    else:
                        json_str = code_block  # 没有结束标记，使用剩余内容
            # 尝试提取 ``` ... ``` 代码块
            elif "```" in response:
                parts = response.split("```", 2)  # 最多分割2次
                if len(parts) >= 2:
                    json_str = parts[1]

            # 清理 JSON 字符串
            json_str = json_str.strip()
            if not json_str:
                raise ValueError("提取的 JSON 内容为空")

            data = json.loads(json_str)

            result.summary = data.get("summary", "")
            result.keyword_analysis = data.get("keyword_analysis", "")
            result.sentiment = data.get("sentiment", "")
            result.cross_platform = data.get("cross_platform", "")
            result.impact = data.get("impact", "")
            result.signals = data.get("signals", "")
            result.conclusion = data.get("conclusion", "")
            result.success = True

        except json.JSONDecodeError as e:
            # JSON 解析失败，记录详细错误但仍使用原始文本
            error_context = json_str[max(0, e.pos - 30):e.pos + 30] if json_str and e.pos else ""
            result.error = f"JSON 解析错误 (位置 {e.pos}): {e.msg}"
            if error_context:
                result.error += f"，上下文: ...{error_context}..."
            # 使用原始响应作为 summary
            result.summary = response[:1000] if len(response) > 1000 else response
            result.success = True  # 仍标记为成功，因为有内容可展示
        except (IndexError, KeyError, TypeError, ValueError) as e:
            # 其他解析错误
            result.error = f"响应解析错误: {type(e).__name__}: {str(e)}"
            result.summary = response[:1000] if len(response) > 1000 else response
            result.success = True
        except Exception as e:
            # 未知错误
            result.error = f"解析时发生未知错误: {type(e).__name__}: {str(e)}"
            result.summary = response[:1000] if len(response) > 1000 else response
            result.success = True

        return result
