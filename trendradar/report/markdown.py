# coding=utf-8
"""
Markdown 报告生成器

生成 Markdown 格式的热点新闻报告，便于分享和存档
参考 DeepResearch 风格设计
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from trendradar.report.helpers import clean_title


def render_markdown_content(
    report_data: Dict,
    total_titles: int,
    is_daily_summary: bool = False,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    *,
    ai_analysis: Optional[Dict] = None,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    get_time_func: Optional[Any] = None,
) -> str:
    """渲染 Markdown 报告内容

    Args:
        report_data: 报告数据字典
        total_titles: 新闻总数
        is_daily_summary: 是否为当日汇总
        mode: 报告模式
        update_info: 更新信息
        ai_analysis: AI 分析结果字典，包含 daily_briefing, insights, categories
        rss_items: RSS 统计条目列表
        rss_new_items: RSS 新增条目列表
        get_time_func: 获取当前时间的函数

    Returns:
        渲染后的 Markdown 字符串
    """
    if get_time_func:
        now = get_time_func()
    else:
        now = datetime.now()
    
    date_str = now.strftime('%Y年%m月%d日')
    time_str = now.strftime('%H:%M')
    
    # 报告类型
    if is_daily_summary:
        if mode == "current":
            report_type = "当前榜单"
        elif mode == "incremental":
            report_type = "增量模式"
        else:
            report_type = "当日汇总"
    else:
        report_type = "实时分析"
    
    # 计算热点新闻数量
    hot_news_count = sum(len(stat["titles"]) for stat in report_data.get("stats", []))
    
    md = []
    
    # 报告头部 (参考 DeepResearch 风格)
    md.append(f"# 📰 每日热点简报")
    md.append(f"")
    md.append(f"> **日期**：{date_str}  ")
    md.append(f"> **类型**：{report_type}  ")
    md.append(f"> **新闻总数**：{total_titles} 条  ")
    md.append(f"> **热点新闻**：{hot_news_count} 条  ")
    md.append(f"> **生成时间**：{time_str}")
    md.append(f"")
    md.append(f"---")
    md.append(f"")
    
    # AI 分析摘要区块 (核心新增)
    if ai_analysis:
        # 每日简报
        daily_briefing = ai_analysis.get('daily_briefing', '')
        if daily_briefing:
            md.append(f"## 📋 AI 智能简报")
            md.append(f"")
            md.append(daily_briefing)
            md.append(f"")
            md.append(f"---")
            md.append(f"")
        
        # 核心洞察
        insights = ai_analysis.get('insights', [])
        if insights:
            md.append(f"## 💡 今日洞察")
            md.append(f"")
            for insight in insights:
                domain = insight.get('domain', '综合')
                content = insight.get('content', '')
                md.append(f"- **[{domain}]** {content}")
            md.append(f"")
            md.append(f"---")
            md.append(f"")
    
    # 热点新闻统计
    if report_data.get("stats"):
        md.append(f"## 🔥 热点新闻统计")
        md.append(f"")
        
        for i, stat in enumerate(report_data["stats"], 1):
            word = stat["word"]
            count = stat["count"]
            
            md.append(f"### {i}. {word} ({count}条)")
            md.append(f"")
            
            for j, title_data in enumerate(stat["titles"], 1):
                title = clean_title(title_data["title"])
                source = title_data.get("source_name", "")
                url = title_data.get("url", "") or title_data.get("mobile_url", "")
                ranks = title_data.get("ranks", [])
                is_new = title_data.get("is_new", False)
                
                # 构建排名显示
                rank_str = ""
                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)
                    if min_rank == max_rank:
                        rank_str = f" `#{min_rank}`"
                    else:
                        rank_str = f" `#{min_rank}-{max_rank}`"
                
                # 构建新闻条目
                new_tag = " 🆕" if is_new else ""
                if url:
                    md.append(f"{j}. [{title}]({url}){rank_str}{new_tag}")
                else:
                    md.append(f"{j}. {title}{rank_str}{new_tag}")
                
                if source:
                    md.append(f"   - 来源: {source}")
            
            md.append(f"")
    
    # 新增热点
    if report_data.get("new_titles"):
        md.append(f"## 🆕 本次新增热点")
        md.append(f"")
        md.append(f"共 {report_data.get('total_new_count', 0)} 条新增")
        md.append(f"")
        
        for source_data in report_data["new_titles"]:
            source_name = source_data["source_name"]
            titles = source_data["titles"]
            
            md.append(f"### {source_name} ({len(titles)}条)")
            md.append(f"")
            
            for i, title_data in enumerate(titles, 1):
                title = clean_title(title_data["title"])
                url = title_data.get("url", "") or title_data.get("mobile_url", "")
                ranks = title_data.get("ranks", [])
                
                rank_str = ""
                if ranks:
                    rank_str = f" `#{min(ranks)}`"
                
                if url:
                    md.append(f"{i}. [{title}]({url}){rank_str}")
                else:
                    md.append(f"{i}. {title}{rank_str}")
            
            md.append(f"")
    
    # RSS 订阅更新
    if rss_items:
        md.append(f"## 📡 RSS 订阅更新")
        md.append(f"")
        
        for stat in rss_items:
            keyword = stat.get("word", "")
            titles = stat.get("titles", [])
            if not titles:
                continue
            
            md.append(f"### {keyword} ({len(titles)}条)")
            md.append(f"")
            
            for i, title_data in enumerate(titles, 1):
                title = clean_title(title_data.get("title", ""))
                url = title_data.get("url", "")
                source = title_data.get("source_name", "")
                time_display = title_data.get("time_display", "")
                
                if url:
                    md.append(f"{i}. [{title}]({url})")
                else:
                    md.append(f"{i}. {title}")
                
                meta_parts = []
                if source:
                    meta_parts.append(f"来源: {source}")
                if time_display:
                    meta_parts.append(f"时间: {time_display}")
                if meta_parts:
                    md.append(f"   - {' | '.join(meta_parts)}")
            
            md.append(f"")
    
    # RSS 新增更新
    if rss_new_items:
        md.append(f"## 📡 RSS 新增更新")
        md.append(f"")
        
        for stat in rss_new_items:
            keyword = stat.get("word", "")
            titles = stat.get("titles", [])
            if not titles:
                continue
            
            md.append(f"### {keyword} ({len(titles)}条)")
            md.append(f"")
            
            for i, title_data in enumerate(titles, 1):
                title = clean_title(title_data.get("title", ""))
                url = title_data.get("url", "")
                
                if url:
                    md.append(f"{i}. [{title}]({url}) 🆕")
                else:
                    md.append(f"{i}. {title} 🆕")
            
            md.append(f"")
    
    # 失败的平台
    if report_data.get("failed_ids"):
        md.append(f"## ⚠️ 请求失败的平台")
        md.append(f"")
        for failed_id in report_data["failed_ids"]:
            md.append(f"- `{failed_id}`")
        md.append(f"")
    
    # 页脚
    md.append(f"---")
    md.append(f"")
    md.append(f"*由 [TrendRadar](https://github.com/sansan0/TrendRadar) 生成*")
    
    if update_info:
        md.append(f"")
        md.append(f"⚠️ 发现新版本 {update_info['remote_version']}，当前版本 {update_info['current_version']}")
    
    return "\n".join(md)


def generate_markdown_report(
    stats: List[Dict],
    total_titles: int,
    failed_ids: Optional[List] = None,
    new_titles: Optional[Dict] = None,
    id_to_name: Optional[Dict] = None,
    mode: str = "daily",
    is_daily_summary: bool = False,
    update_info: Optional[Dict] = None,
    rank_threshold: int = 3,
    output_dir: str = "output",
    date_folder: str = "",
    time_filename: str = "",
    ai_analysis: Optional[Dict] = None,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    prepare_report_data_func: Optional[Any] = None,
) -> str:
    """
    生成 Markdown 报告

    Args:
        stats: 统计结果列表
        total_titles: 总标题数
        failed_ids: 失败的 ID 列表
        new_titles: 新增标题
        id_to_name: ID 到名称的映射
        mode: 报告模式
        is_daily_summary: 是否是每日汇总
        update_info: 更新信息
        rank_threshold: 排名阈值
        output_dir: 输出目录
        date_folder: 日期文件夹名称
        time_filename: 时间文件名
        ai_analysis: AI 分析结果
        rss_items: RSS 条目
        rss_new_items: RSS 新增条目
        prepare_report_data_func: 准备报告数据的函数

    Returns:
        str: 生成的 Markdown 文件路径
    """
    if is_daily_summary:
        if mode == "current":
            filename = "当前榜单汇总.md"
        elif mode == "incremental":
            filename = "当日增量.md"
        else:
            filename = "当日汇总.md"
    else:
        filename = f"{time_filename}.md"

    # 构建输出路径
    output_path = Path(output_dir) / date_folder / "markdown"
    output_path.mkdir(parents=True, exist_ok=True)
    file_path = str(output_path / filename)

    # 准备报告数据
    if prepare_report_data_func:
        report_data = prepare_report_data_func(
            stats,
            failed_ids,
            new_titles,
            id_to_name,
            mode,
            rank_threshold,
        )
    else:
        # 简单处理
        report_data = {
            "stats": stats,
            "new_titles": [],
            "failed_ids": failed_ids or [],
            "total_new_count": 0,
        }

    # 渲染 Markdown 内容
    md_content = render_markdown_content(
        report_data,
        total_titles,
        is_daily_summary,
        mode,
        update_info,
        ai_analysis=ai_analysis,
        rss_items=rss_items,
        rss_new_items=rss_new_items,
    )

    # 写入文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return file_path
