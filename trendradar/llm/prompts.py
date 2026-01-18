"""
Prompt 模板管理

管理 AI 分析使用的各种 Prompt 模板
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class PromptTemplate:
    """Prompt 模板"""
    name: str
    system_prompt: str
    user_prompt_template: str
    description: str = ""
    
    def render(self, **kwargs) -> str:
        """渲染用户 Prompt"""
        return self.user_prompt_template.format(**kwargs)


class PromptManager:
    """Prompt 模板管理器"""
    
    # 系统角色定义
    SYSTEM_ANALYST = """你是一位专业的新闻分析师和内容编辑，擅长：
- 快速提取新闻核心信息
- 识别新闻之间的关联性
- 发现趋势和洞察
- 用简洁专业的语言进行总结

你的输出应该：
- 客观、准确、有价值
- 使用中文回复
- 格式清晰，便于阅读
"""
    
    SYSTEM_CATEGORIZER = """你是一位专业的内容分类专家，擅长：
- 准确识别新闻主题和领域
- 理解新闻的核心内容
- 进行多维度分类

你需要将新闻准确分类到预定义的类别中。
"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化 Prompt 管理器"""
        self.config = config or {}
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """加载默认模板"""
        
        # 每日简报模板
        self.templates['daily_briefing'] = PromptTemplate(
            name='daily_briefing',
            description='生成每日新闻简报',
            system_prompt=self.SYSTEM_ANALYST,
            user_prompt_template="""请根据以下今日热点新闻，生成一份专业的每日简报。

## 今日热点新闻
{news_content}

## 要求
1. 按领域分类整理（如：AI/科技、财经、社会等）
2. 每个领域写一段核心摘要（2-3句话概括重点）
3. 列出该领域的重要新闻（标题+一句话简介）
4. 最后提供3-5条今日洞察（重要趋势、关键数据、值得关注的点）

## 输出格式
使用 Markdown 格式，结构如下：

# 每日热点简报
日期：{date}

## 🔥 [领域名称] (N条)
【核心摘要】...

1. **新闻标题**
   简介...
   来源：...

## 📊 今日洞察
- 洞察1
- 洞察2
...

---
请开始生成简报："""
        )
        
        # 智能分类模板
        self.templates['categorize'] = PromptTemplate(
            name='categorize',
            description='对新闻进行智能分类',
            system_prompt=self.SYSTEM_CATEGORIZER,
            user_prompt_template="""请将以下新闻分类到最合适的类别中。

## 新闻内容
标题：{title}
正文：{content}

## 可选类别
{categories}

## 要求
1. 选择最匹配的1-2个类别
2. 给出分类置信度（0-100）
3. 简要说明分类理由

## 输出格式（JSON）
{{
    "primary_category": "类别ID",
    "secondary_category": "类别ID或null",
    "confidence": 85,
    "reason": "简要理由"
}}

请输出 JSON："""
        )
        
        # 洞察提取模板
        self.templates['extract_insights'] = PromptTemplate(
            name='extract_insights',
            description='提取新闻核心洞察',
            system_prompt=self.SYSTEM_ANALYST,
            user_prompt_template="""请分析以下新闻，提取核心洞察。

## 新闻内容
{news_content}

## 要求
1. 提取3-5条核心洞察
2. 每条洞察应该：
   - 揭示重要趋势或规律
   - 包含关键数据或事实
   - 具有前瞻性或警示意义
3. 语言简洁，每条不超过50字

## 输出格式
1. [领域] 洞察内容
2. [领域] 洞察内容
...

请提取洞察："""
        )
        
        # 新闻摘要模板
        self.templates['summarize'] = PromptTemplate(
            name='summarize',
            description='生成新闻摘要',
            system_prompt=self.SYSTEM_ANALYST,
            user_prompt_template="""请为以下新闻生成简洁的摘要。

## 新闻内容
标题：{title}
正文：{content}

## 要求
1. 摘要长度：50-100字
2. 保留核心信息：谁、什么、何时、为什么
3. 语言客观简洁

请输出摘要："""
        )
        
        # 深度研究报告模板（参考 DeepResearch 格式）
        self.templates['deep_research'] = PromptTemplate(
            name='deep_research',
            description='生成深度研究报告',
            system_prompt="""你是一位资深的研究分析师，擅长撰写专业的深度研究报告。
你的报告应该：
- 结构清晰，逻辑严谨
- 引用具体事实和数据
- 提供独立的分析观点
- 指出局限性和未解决问题
""",
            user_prompt_template="""请根据以下新闻和相关信息，生成一份深度研究报告。

## 主题
{topic}

## 相关新闻
{news_content}

## 报告结构要求

### 1. 摘要
- 3-5个核心要点
- 每个要点带来源标注

### 2. 背景
- 主题背景介绍
- 为什么这个话题重要

### 3. 深度分析
- 分多个维度详细分析
- 包含具体数据和事实
- 引用多个来源

### 4. 结论与建议
- 核心结论
- 可行建议
- 未解决的问题

### 5. 数据与引用
- 列出所有引用来源

## 输出格式
使用 Markdown 格式，包含清晰的标题层级。

日期：{date}

请开始撰写报告："""
        )
        
        # 批量分类模板
        self.templates['batch_categorize'] = PromptTemplate(
            name='batch_categorize',
            description='批量分类多条新闻',
            system_prompt=self.SYSTEM_CATEGORIZER,
            user_prompt_template="""请将以下新闻列表分类到对应类别。

## 新闻列表
{news_list}

## 可选类别
{categories}

## 要求
1. 为每条新闻选择最匹配的类别
2. 输出 JSON 格式

## 输出格式
[
    {{"id": 1, "category": "类别ID"}},
    {{"id": 2, "category": "类别ID"}},
    ...
]

请输出分类结果："""
        )
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """获取指定模板"""
        return self.templates.get(name)
    
    def render_daily_briefing(
        self,
        news_items: List[Dict[str, Any]],
        date: str = None
    ) -> tuple:
        """
        渲染每日简报 Prompt
        
        Args:
            news_items: 新闻列表，每项包含 title, content, source 等
            date: 日期字符串
            
        Returns:
            tuple: (system_prompt, user_prompt)
        """
        template = self.templates['daily_briefing']
        
        if date is None:
            date = datetime.now().strftime('%Y年%m月%d日')
        
        # 格式化新闻内容
        news_content = self._format_news_list(news_items)
        
        user_prompt = template.render(
            news_content=news_content,
            date=date
        )
        
        return template.system_prompt, user_prompt
    
    def render_categorize(
        self,
        title: str,
        content: str,
        categories: List[Dict[str, Any]]
    ) -> tuple:
        """
        渲染分类 Prompt
        
        Args:
            title: 新闻标题
            content: 新闻内容
            categories: 类别列表
            
        Returns:
            tuple: (system_prompt, user_prompt)
        """
        template = self.templates['categorize']
        
        # 格式化类别
        categories_text = "\n".join([
            f"- {cat['id']}: {cat['name']} (关键词: {', '.join(cat.get('keywords', [])[:5])})"
            for cat in categories
        ])
        
        # 截断内容避免过长
        content = content[:2000] if len(content) > 2000 else content
        
        user_prompt = template.render(
            title=title,
            content=content,
            categories=categories_text
        )
        
        return template.system_prompt, user_prompt
    
    def render_insights(self, news_items: List[Dict[str, Any]]) -> tuple:
        """渲染洞察提取 Prompt"""
        template = self.templates['extract_insights']
        
        news_content = self._format_news_list(news_items)
        user_prompt = template.render(news_content=news_content)
        
        return template.system_prompt, user_prompt
    
    def render_summarize(self, title: str, content: str) -> tuple:
        """渲染摘要 Prompt"""
        template = self.templates['summarize']
        
        content = content[:3000] if len(content) > 3000 else content
        user_prompt = template.render(title=title, content=content)
        
        return template.system_prompt, user_prompt
    
    def render_deep_research(
        self,
        topic: str,
        news_items: List[Dict[str, Any]],
        date: str = None
    ) -> tuple:
        """渲染深度研究报告 Prompt"""
        template = self.templates['deep_research']
        
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        news_content = self._format_news_list(news_items, detailed=True)
        
        user_prompt = template.render(
            topic=topic,
            news_content=news_content,
            date=date
        )
        
        return template.system_prompt, user_prompt
    
    def _format_news_list(
        self,
        news_items: List[Dict[str, Any]],
        detailed: bool = False
    ) -> str:
        """格式化新闻列表"""
        lines = []
        
        for i, item in enumerate(news_items, 1):
            title = item.get('title', '无标题')
            source = item.get('source', '未知来源')
            content = item.get('content', '')
            
            if detailed:
                # 详细模式：包含完整内容
                content_preview = content[:1000] if len(content) > 1000 else content
                lines.append(f"### {i}. {title}")
                lines.append(f"来源：{source}")
                lines.append(f"内容：{content_preview}")
                lines.append("")
            else:
                # 简洁模式：只包含标题和摘要
                content_preview = content[:200] + '...' if len(content) > 200 else content
                lines.append(f"{i}. **{title}** ({source})")
                if content_preview:
                    lines.append(f"   {content_preview}")
                lines.append("")
        
        return "\n".join(lines)
    
    def add_template(self, template: PromptTemplate):
        """添加自定义模板"""
        self.templates[template.name] = template
    
    def list_templates(self) -> List[str]:
        """列出所有可用模板"""
        return list(self.templates.keys())
