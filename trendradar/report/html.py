# coding=utf-8
"""
HTML 报告渲染模块

提供 HTML 格式的热点新闻报告生成功能
"""

from datetime import datetime
from typing import Dict, Optional, Callable

from trendradar.report.helpers import html_escape


def render_html_content(
    report_data: Dict,
    total_titles: int,
    is_daily_summary: bool = False,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    *,
    reverse_content_order: bool = False,
    get_time_func: Optional[Callable[[], datetime]] = None,
) -> str:
    """渲染HTML内容

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        total_titles: 新闻总数
        is_daily_summary: 是否为当日汇总
        mode: 报告模式 ("daily", "current", "incremental")
        update_info: 更新信息（可选）
        reverse_content_order: 是否反转内容顺序（新增热点在前）
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now）

    Returns:
        渲染后的 HTML 字符串
    """
    
    # 准备统计数据
    hot_news_count = sum(len(stat["titles"]) for stat in report_data["stats"])
    topic_count = len(report_data["stats"])
    
    # 计算平台分布
    platform_stats = {}
    for stat in report_data["stats"]:
        for title in stat["titles"]:
            source = title.get("source_name", "未知")
            platform_stats[source] = platform_stats.get(source, 0) + 1
    
    # 获取时间
    if get_time_func:
        now = get_time_func()
    else:
        now = datetime.now()
    
    # 报告类型文案
    report_type_text = "实时分析"
    if is_daily_summary:
        if mode == "current":
            report_type_text = "当前榜单"
        elif mode == "incremental":
            report_type_text = "增量监控"
        else:
            report_type_text = "当日汇总"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TrendRadar 热点聚合 - {now.strftime("%m-%d")}</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <style>
            :root {{
                --bg-color: #f0f2f5;
                --card-bg: #ffffff;
                --text-main: #1f2937;
                --text-sub: #6b7280;
                --accent-color: #3b82f6;
                --danger-color: #ef4444;
                --success-color: #10b981;
                --warning-color: #f59e0b;
                --border-radius: 12px;
                --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                --header-gradient: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            }}

            * {{ box-sizing: border-box; }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 24px;
                background-color: var(--bg-color);
                color: var(--text-main);
                line-height: 1.5;
            }}

            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}

            /* --- Header Area --- */
            .dashboard-header {{
                background: var(--header-gradient);
                color: white;
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 32px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                position: relative;
                overflow: hidden;
            }}

            .header-top {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 32px;
                position: relative;
                z-index: 2;
            }}

            .brand-section h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 800;
                letter-spacing: -0.5px;
                background: linear-gradient(to right, #60a5fa, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                display: none;
            }}

            .brand-section p {{
                margin: 0;
                opacity: 0.9;
                font-size: 16px;
                font-weight: 600;
            }}

            .action-buttons {{
                display: flex;
                gap: 12px;
            }}

            .btn {{
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: white;
                padding: 8px 16px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 600;
                transition: all 0.2s;
                backdrop-filter: blur(4px);
            }}

            .btn:hover {{
                background: rgba(255, 255, 255, 0.2);
                transform: translateY(-1px);
            }}

            .stats-row {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 24px;
                position: relative;
                z-index: 2;
                margin-bottom: 24px;
            }}

            .stat-card {{
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 16px 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}

            .stat-label {{
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1px;
                opacity: 0.6;
                margin-bottom: 4px;
                display: block;
            }}

            .stat-value {{
                font-size: 28px;
                font-weight: 700;
                letter-spacing: -1px;
            }}
            
            .stat-sub {{
                font-size: 12px;
                opacity: 0.8;
                margin-left: 4px;
                font-weight: 400;
            }}

            /* 数据可视化区域 */
            .charts-section {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
                margin-top: 24px;
            }}

            .chart-container {{
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                height: 300px;
                display: flex;
                flex-direction: column;
            }}

            .chart-title {{
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 12px;
                opacity: 0.8;
                flex-shrink: 0;
            }}
            
            .chart-wrapper {{
                flex: 1;
                position: relative;
                min-height: 0;
            }}
            
            .chart-wrapper canvas {{
                max-height: 100%;
            }}

            /* --- Multi-Column Layout --- */
            .masonry-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 24px;
                align-items: start;
            }}
            
            @media (max-width: 1200px) {{
                .masonry-grid {{
                    grid-template-columns: repeat(2, 1fr);
                }}
            }}
            
            @media (max-width: 768px) {{
                .masonry-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            /* 新增卡片放在右上角 */
            .new-section-card {{
                grid-column: 3;
                grid-row: 1;
            }}
            
            @media (max-width: 1200px) {{
                .new-section-card {{
                    grid-column: 2;
                    grid-row: 1;
                }}
            }}
            
            @media (max-width: 768px) {{
                .new-section-card {{
                    grid-column: 1;
                    grid-row: 1;
                }}
            }}

            .card {{
                background: var(--card-bg);
                border-radius: var(--border-radius);
                box-shadow: var(--card-shadow);
                overflow: hidden;
                transition: transform 0.2s, box-shadow 0.2s;
                border: 1px solid rgba(0,0,0,0.03);
                display: flex;
                flex-direction: column;
            }}

            .card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
            }}

            /* Card Header - 可点击展开/收起 */
            .card-header {{
                padding: 16px 20px;
                border-bottom: 1px solid #f3f4f6;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #ffffff;
                position: relative;
                cursor: pointer;
                user-select: none;
            }}
            
            .card-header:hover {{
                background: #f9fafb;
            }}
            
            .card-header::before {{
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: var(--accent-color);
            }}
            
            .card-header.hot::before {{ background: var(--danger-color); }}
            .card-header.warm::before {{ background: var(--warning-color); }}
            .card-header.new-section::before {{ background: var(--success-color); }}

            .topic-title {{
                font-size: 18px;
                font-weight: 700;
                color: var(--text-main);
                display: flex;
                flex-direction: column;
                align-items: flex-start;
                gap: 4px;
            }}
            
            .topic-main {{
                font-size: 18px;
                font-weight: 700;
            }}
            
            .topic-keywords {{
                font-size: 11px;
                font-weight: 400;
                color: #9ca3af;
                line-height: 1.4;
            }}

            .topic-count {{
                background: #f3f4f6;
                color: var(--text-sub);
                font-size: 12px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 20px;
            }}
            
            .topic-count.hot {{
                background: #fee2e2;
                color: #ef4444;
            }}

            .expand-icon {{
                font-size: 20px;
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                color: #9ca3af;
                display: inline-block;
            }}

            .card.collapsed .expand-icon {{
                transform: rotate(-90deg);
            }}
            
            .card-header:hover .expand-icon {{
                color: #3b82f6;
            }}

            /* News List - 可展开收起 */
            .news-list {{
                padding: 8px 0;
                max-height: 2000px;
                overflow: hidden;
                transition: max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease;
                opacity: 1;
            }}

            /* 折叠状态：只显示前3条新闻 */
            .card.collapsed .news-list {{
                max-height: 300px;
                overflow: hidden;
            }}
            
            .card.collapsed .news-item:nth-child(n+4) {{
                opacity: 0;
                transform: translateY(-10px);
                transition: opacity 0.2s ease, transform 0.2s ease;
            }}
            
            .news-item {{
                opacity: 1;
                transform: translateY(0);
                transition: opacity 0.3s ease, transform 0.3s ease, background 0.2s;
            }}
            
            /* 折叠提示：在新闻列表底部显示 */
            .card.collapsed .news-list::after {{
                content: '点击标题查看全部';
                display: block;
                text-align: center;
                padding: 12px;
                font-size: 12px;
                color: #9ca3af;
                font-style: italic;
            }}
            
            /* 滚动条样式 */
            .news-list::-webkit-scrollbar {{
                width: 6px;
            }}
            
            .news-list::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 3px;
            }}
            
            .news-list::-webkit-scrollbar-thumb {{
                background: #cbd5e1;
                border-radius: 3px;
            }}
            
            .news-list::-webkit-scrollbar-thumb:hover {{
                background: #94a3b8;
            }}

            .news-item {{
                padding: 12px 20px;
                border-bottom: 1px solid #f9fafb;
                display: flex;
                gap: 12px;
                align-items: flex-start;
            }}

            .news-item:last-child {{
                border-bottom: none;
            }}
            
            .news-item:hover {{
                background-color: #f9fafb;
            }}

            .news-index {{
                color: #9ca3af;
                font-size: 14px;
                font-weight: 500;
                min-width: 20px;
                padding-top: 2px;
            }}

            .news-content {{
                flex: 1;
            }}

            .news-meta {{
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 4px;
                font-size: 11px;
            }}

            .tag {{
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: 600;
            }}
            
            .tag-source {{
                background: #eff6ff;
                color: #3b82f6;
            }}
            
            .tag-new {{
                background: #ecfdf5;
                color: #059669;
                text-transform: uppercase;
            }}
            
            .tag-time {{
                color: #9ca3af;
            }}

            .news-link {{
                color: var(--text-main);
                text-decoration: none;
                font-size: 14px;
                font-weight: 500;
                line-height: 1.4;
                display: block;
                transition: color 0.2s;
            }}

            .news-link:hover {{
                color: var(--accent-color);
            }}
            
            /* 新闻摘要预览 */
            .news-preview {{
                margin-top: 8px;
                padding: 8px 12px;
                background: #f9fafb;
                border-left: 3px solid #e5e7eb;
                font-size: 13px;
                color: #6b7280;
                line-height: 1.5;
                border-radius: 4px;
                display: none;
            }}

            .news-item.show-preview .news-preview {{
                display: block;
            }}

            .preview-toggle {{
                font-size: 11px;
                color: #3b82f6;
                cursor: pointer;
                margin-top: 4px;
                display: inline-block;
            }}

            .preview-toggle:hover {{
                text-decoration: underline;
            }}
            
            .rank-indicator {{
                display: inline-block;
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background-color: #d1d5db;
                margin-right: 4px;
            }}
            
            .rank-indicator.top {{ background-color: #ef4444; }}
            .rank-indicator.high {{ background-color: #f97316; }}

            /* New Section Special Style */
            .new-section-card .card-header {{
                background: #ecfdf5;
                border-bottom: 1px solid #d1fae5;
            }}
            
            .new-section-card .topic-title {{
                color: #065f46;
            }}

            /* Error Section */
            .error-card {{
                background: #fff5f5;
                border: 1px solid #feb2b2;
                padding: 16px;
                margin-bottom: 24px;
                border-radius: 8px;
                color: #c53030;
            }}

            /* Footer */
            .footer {{
                text-align: center;
                padding: 40px 0;
                color: var(--text-sub);
                font-size: 13px;
            }}

            .footer a {{
                color: var(--text-sub);
                text-decoration: none;
                border-bottom: 1px dotted #9ca3af;
            }}

            @media (max-width: 600px) {{
                body {{ padding: 12px; }}
                .dashboard-header {{ padding: 20px; border-radius: 12px; }}
                .stats-row {{ grid-template-columns: 1fr 1fr; gap: 16px; }}
                .header-top {{ flex-direction: column; gap: 16px; }}
                .action-buttons {{ width: 100%; }}
                .btn {{ flex: 1; text-align: center; }}
                .charts-section {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="container" id="capture-container">
            <!-- Header -->
            <div class="dashboard-header">
                <div class="header-top">
                    <div class="brand-section">
                        <h1>TrendRadar</h1>
                        <p>全网热点聚合分析报告</p>
                </div>
                    <div class="action-buttons" data-html2canvas-ignore>
                        <div class="btn" onclick="saveAsImage()">保存图片</div>
                        <div class="btn" onclick="saveAsMultipleImages()">分段保存</div>
                    </div>
                    </div>
                
                <div class="stats-row">
                    <div class="stat-card">
                        <span class="stat-label">新闻总数</span>
                        <span class="stat-value">{total_titles}<span class="stat-sub">条</span></span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">热点话题</span>
                        <span class="stat-value">{topic_count}<span class="stat-sub">个</span></span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">报告类型</span>
                        <span class="stat-value" style="font-size: 20px;">{report_type_text}</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">生成时间</span>
                        <span class="stat-value" style="font-size: 20px;">{now.strftime("%H:%M")}</span>
                    </div>
                </div>

                <!-- 数据可视化 -->
                <div class="charts-section">
                    <div class="chart-container">
                        <div class="chart-title">📊 热度趋势</div>
                        <div class="chart-wrapper">
                            <canvas id="trendChart"></canvas>
                        </div>
                    </div>
                    <div class="chart-container">
                        <div class="chart-title">📱 平台分布</div>
                        <div class="chart-wrapper">
                            <canvas id="platformChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Error Display -->
            """

    if report_data["failed_ids"]:
        html += """
            <div class="error-card">
                <strong>⚠️ 部分平台获取失败：</strong>
                """ + ", ".join(html_escape(fid) for fid in report_data["failed_ids"]) + """
                        </div>
        """

        html += """
            <!-- Content Grid -->
            <div class="masonry-grid">
    """

    # --- 1. 新增热点卡片 ---
    new_section_html = ""
    if report_data["new_titles"]:
        new_section_html = f"""
            <div class="card new-section-card">
                <div class="card-header new-section" onclick="toggleCard(this)">
                    <div class="topic-title">
                        ⚡ 本次新增
                        </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span class="topic-count">{report_data['total_new_count']} 条</span>
                        <span class="expand-icon">▼</span>
                            </div>
                        </div>
                <div class="news-list">
        """
        
        idx_counter = 1
        for source_data in report_data["new_titles"]:
            source_name = html_escape(source_data["source_name"])
            
            for title_data in source_data["titles"]:
                title = html_escape(title_data["title"])
                url = title_data.get("mobile_url") or title_data.get("url", "")
                
                ranks = title_data.get("ranks", [])
                rank_class = ""
                if ranks:
                    min_rank = min(ranks)
                    if min_rank <= 3: rank_class = "top"
                    elif min_rank <= 10: rank_class = "high"
                
                new_section_html += f"""
                    <div class="news-item">
                        <div class="news-index">{idx_counter}</div>
                        <div class="news-content">
                            <div class="news-meta">
                                <span class="tag tag-source">{source_name}</span>
                                <span class="rank-indicator {rank_class}"></span>
                            </div>
                            <a href="{html_escape(url) if url else 'javascript:void(0)'}" 
                               class="news-link" target="_blank">{title}</a>
                            <div class="preview-toggle" onclick="togglePreview(this)">💡 说明</div>
                            <div class="news-preview">
                                📌 本项目抓取各平台热榜数据，仅包含标题和链接。点击标题可跳转到原文查看完整内容。
                            </div>
                        </div>
                    </div>
                """
                idx_counter += 1
                
        new_section_html += """
                </div>
            </div>
        """

    # --- 2. 热点词汇卡片 ---
    stats_section_html = ""
    for stat in report_data["stats"]:
        word = html_escape(stat["word"])
        count = stat["count"]
        
        # 拆分标题：如果包含 === 分隔符，提取主标题和关键词
        main_title = word
        keywords = ""
        if "===" in word:
            parts = word.split("===")
            if len(parts) >= 2:
                main_title = parts[1].strip()
                # 获取第三部分作为关键词（如果存在）
                if len(parts) >= 3:
                    keywords = parts[2].strip()
        
        header_class = "normal"
        count_class = "normal"
        if count >= 10:
            header_class = "hot"
            count_class = "hot"
        elif count >= 5:
            header_class = "warm"
        
        stats_section_html += f"""
            <div class="card">
                <div class="card-header {header_class}" onclick="toggleCard(this)">
                    <div class="topic-title">
                        <div class="topic-main">{main_title}</div>
                        {f'<div class="topic-keywords">{keywords}</div>' if keywords else ''}
                            </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span class="topic-count {count_class}">{count} 条</span>
                        <span class="expand-icon">▼</span>
                            </div>
                        </div>
                <div class="news-list">
        """
        
        # 排序：优先按热度（hotness），其次按时间（时间越新越靠前）
        sorted_titles = sorted(
            stat["titles"],
            key=lambda x: (
                -(x.get("hotness", 0) or 0),  # 热度降序（负号表示从高到低）
                -(x.get("timestamp", 0) or 0)  # 时间降序（越新越靠前）
            )
        )
        
        for idx, title_data in enumerate(sorted_titles, 1):
            title = html_escape(title_data["title"])
            source = html_escape(title_data["source_name"])
            url = title_data.get("mobile_url") or title_data.get("url", "")
            is_new = title_data.get("is_new", False)
            
            time_display = title_data.get("time_display", "")
            if time_display:
                # 清理时间显示格式：[10:49 ~ 19:16] -> 10:49-19:16
                time_display = time_display.replace("[", "").replace("]", "").replace(" ~ ", "-").strip()
            
            stats_section_html += f"""
                <div class="news-item">
                    <div class="news-index">{idx}</div>
                    <div class="news-content">
                        <div class="news-meta">
                            <span class="tag tag-source">{source}</span>
                            {f'<span class="tag tag-new">NEW</span>' if is_new else ''}
                            {f'<span class="tag tag-time">{html_escape(time_display)}</span>' if time_display else ''}
                        </div>
                        <a href="{html_escape(url) if url else 'javascript:void(0)'}" 
                           class="news-link" target="_blank">{title}</a>
                        <div class="preview-toggle" onclick="togglePreview(this)">💡 说明</div>
                        <div class="news-preview">
                            📌 本项目抓取各平台热榜数据，仅包含标题和链接。点击标题可跳转到原文查看完整内容。
                        </div>
                    </div>
                </div>
            """
            
        stats_section_html += """
                                </div>
                            </div>
        """

    # 组合内容
    if reverse_content_order:
        html += new_section_html + stats_section_html
    else:
        html += stats_section_html + new_section_html

    # 准备图表数据
    topic_labels = []
    topic_counts = []
    for stat in report_data["stats"][:8]:
        word = stat["word"]
        # 提取主标题（如果有===分隔符）
        if "===" in word:
            parts = word.split("===")
            if len(parts) >= 2:
                word = parts[1].strip()
        # 截取长度
        if len(word) > 8:
            word = word[:8] + "..."
        topic_labels.append(word)
        topic_counts.append(stat["count"])
    
    platform_labels = list(platform_stats.keys())[:6]  # 最多6个平台
    platform_counts = [platform_stats[k] for k in platform_labels]

    # 生成footer
    footer_html = f"""
            </div> <!-- End Masonry Grid -->

            <div class="footer">
                <p>
                    生成于 {now.strftime("%Y-%m-%d %H:%M:%S")}
                </p>
    """
    if update_info:
        footer_html += f"""
                <p class="update-info">发现新版本 {update_info["remote_version"]}</p>
    """
    footer_html += """
            </div>
        </div>
    """
    
    html += footer_html
    
    # 转换为JSON格式
    import json
    topic_labels_json = json.dumps(topic_labels, ensure_ascii=False)
    topic_counts_json = json.dumps(topic_counts)
    platform_labels_json = json.dumps(platform_labels, ensure_ascii=False)
    platform_counts_json = json.dumps(platform_counts)
    
    html += f"""
        <script>
            // 卡片展开/收起
            function toggleCard(header) {{
                const card = header.closest('.card');
                card.classList.toggle('collapsed');
            }}

            // 新闻说明展开/收起
            function togglePreview(btn) {{
                const newsItem = btn.closest('.news-item');
                newsItem.classList.toggle('show-preview');
                btn.textContent = newsItem.classList.contains('show-preview') 
                    ? '收起 ▲' 
                    : '💡 说明';
            }}

            // 初始化图表
            document.addEventListener('DOMContentLoaded', function() {{
                // 默认折叠所有卡片（显示前3条新闻）
                document.querySelectorAll('.card').forEach(card => {{
                    const newsItems = card.querySelectorAll('.news-item');
                    if (newsItems.length > 3) {{
                        card.classList.add('collapsed');
                    }}
                }});

                // 热度趋势图
                const trendCtx = document.getElementById('trendChart').getContext('2d');
                new Chart(trendCtx, {{
                    type: 'bar',
                    data: {{
                        labels: {topic_labels_json},
                        datasets: [{{
                            label: '新闻数量',
                            data: {topic_counts_json},
                            backgroundColor: 'rgba(59, 130, 246, 0.6)',
                            borderColor: 'rgba(59, 130, 246, 1)',
                            borderWidth: 2,
                            borderRadius: 6
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ display: false }},
                            tooltip: {{
                                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                padding: 12,
                                titleColor: '#fff',
                                bodyColor: '#fff'
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                ticks: {{ 
                                    color: 'rgba(255,255,255,0.6)',
                                    precision: 0
                                }},
                                grid: {{ color: 'rgba(255,255,255,0.1)' }}
                            }},
                            x: {{
                                ticks: {{ 
                                    color: 'rgba(255,255,255,0.6)',
                                    maxRotation: 45,
                                    minRotation: 45,
                                    autoSkip: false
                                }},
                                grid: {{ display: false }}
                            }}
                        }}
                    }}
                }});

                // 平台分布图
                const platformCtx = document.getElementById('platformChart').getContext('2d');
                new Chart(platformCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: {platform_labels_json},
                        datasets: [{{
                            data: {platform_counts_json},
                            backgroundColor: [
                                'rgba(59, 130, 246, 0.8)',
                                'rgba(16, 185, 129, 0.8)',
                                'rgba(245, 158, 11, 0.8)',
                                'rgba(239, 68, 68, 0.8)',
                                'rgba(139, 92, 246, 0.8)',
                                'rgba(236, 72, 153, 0.8)'
                            ],
                            borderWidth: 0
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{
                                    color: 'rgba(255,255,255,0.8)',
                                    padding: 10,
                                    font: {{ size: 11 }}
                                }}
                            }},
                            tooltip: {{
                                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                padding: 12
                            }}
                        }}
                    }}
                }});
            }});

            // 截图功能
            async function saveAsImage() {{
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '生成中...';
                
                try {{
                    const container = document.getElementById('capture-container');
                    const canvas = await html2canvas(container, {{
                        scale: 2,
                        backgroundColor: '#f0f2f5',
                        useCORS: true,
                        logging: false
                    }});

                    const link = document.createElement('a');
                    link.download = 'TrendRadar_Report_{now.strftime("%Y%m%d_%H%M")}.png';
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                    
                    btn.textContent = '已保存';
                }} catch (e) {{
                    console.error(e);
                    btn.textContent = '失败';
                }}
                
                setTimeout(() => btn.textContent = originalText, 2000);
            }}

            async function saveAsMultipleImages() {{
                alert('建议使用"保存图片"功能直接保存完整报告');
            }}
        </script>
    </body>
    </html>
    """
    return html
