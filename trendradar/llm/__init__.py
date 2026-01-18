"""
TrendRadar LLM 模块

提供大语言模型接入和 AI 分析功能：
- 支持 NewAPI / OneAPI / OpenAI 兼容 API
- 每日简报生成
- 智能分类
- 核心洞察提取
- 热点新闻分析
"""

from .client import LLMClient
from .prompts import PromptManager, PromptTemplate
from .analyzer import AIAnalyzer, AnalysisResult, AIAnalysisResult, HotspotAnalyzer
from .formatter import (
    render_ai_analysis_markdown,
    render_ai_analysis_feishu,
    render_ai_analysis_dingtalk,
    render_ai_analysis_html,
    render_ai_analysis_plain,
    get_ai_analysis_renderer,
)

__all__ = [
    'LLMClient',
    'PromptManager',
    'PromptTemplate',
    'AIAnalyzer',
    'AnalysisResult',
    'AIAnalysisResult',
    'HotspotAnalyzer',
    'render_ai_analysis_markdown',
    'render_ai_analysis_feishu',
    'render_ai_analysis_dingtalk',
    'render_ai_analysis_html',
    'render_ai_analysis_plain',
    'get_ai_analysis_renderer',
]
