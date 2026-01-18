# coding=utf-8
"""
PDF 报告生成器

将 HTML 报告转换为 PDF 格式，便于归档和打印
需要安装 weasyprint: pip install weasyprint
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def is_pdf_available() -> bool:
    """检查 PDF 生成功能是否可用"""
    try:
        import weasyprint  # noqa: F401
        return True
    except ImportError:
        return False


def html_to_pdf(html_content: str, output_path: str) -> bool:
    """
    将 HTML 内容转换为 PDF

    Args:
        html_content: HTML 字符串
        output_path: PDF 输出路径

    Returns:
        bool: 是否成功
    """
    try:
        from weasyprint import HTML
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为 PDF
        HTML(string=html_content).write_pdf(output_path)
        
        logger.info(f"PDF 报告已生成: {output_path}")
        return True
        
    except ImportError:
        logger.warning("weasyprint 未安装，无法生成 PDF。请运行: pip install weasyprint")
        return False
    except Exception as e:
        logger.error(f"生成 PDF 失败: {e}")
        return False


def generate_pdf_report(
    html_file_path: str,
    output_dir: str = "output",
    date_folder: str = "",
    filename: Optional[str] = None,
) -> Optional[str]:
    """
    从 HTML 文件生成 PDF 报告

    Args:
        html_file_path: HTML 文件路径
        output_dir: 输出目录
        date_folder: 日期文件夹名称
        filename: 输出文件名（不含扩展名）

    Returns:
        str: PDF 文件路径，失败返回 None
    """
    if not is_pdf_available():
        logger.warning("PDF 生成功能不可用，跳过")
        return None
    
    try:
        # 读取 HTML 内容
        html_path = Path(html_file_path)
        if not html_path.exists():
            logger.error(f"HTML 文件不存在: {html_file_path}")
            return None
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # 确定输出路径
        if filename is None:
            filename = html_path.stem
        
        output_path = Path(output_dir) / date_folder / "pdf"
        output_path.mkdir(parents=True, exist_ok=True)
        pdf_path = str(output_path / f"{filename}.pdf")
        
        # 转换
        if html_to_pdf(html_content, pdf_path):
            return pdf_path
        return None
        
    except Exception as e:
        logger.error(f"生成 PDF 报告失败: {e}")
        return None


def generate_pdf_from_markdown(
    markdown_content: str,
    output_path: str,
    title: str = "热点新闻报告",
) -> bool:
    """
    从 Markdown 内容生成 PDF

    Args:
        markdown_content: Markdown 字符串
        output_path: PDF 输出路径
        title: 文档标题

    Returns:
        bool: 是否成功
    """
    try:
        import markdown
        from weasyprint import HTML
        
        # Markdown 转 HTML
        html_body = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'toc']
        )
        
        # 包装为完整 HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            margin: 40px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #4f46e5;
            border-bottom: 2px solid #4f46e5;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #7c3aed;
            margin-top: 30px;
        }}
        h3 {{
            color: #059669;
        }}
        a {{
            color: #2563eb;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        code {{
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        blockquote {{
            border-left: 4px solid #4f46e5;
            margin: 20px 0;
            padding: 10px 20px;
            background: #f8fafc;
        }}
        ul, ol {{
            margin: 10px 0;
        }}
        li {{
            margin: 5px 0;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e5e7eb;
            margin: 30px 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #e5e7eb;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background: #f3f4f6;
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 转换为 PDF
        HTML(string=html_content).write_pdf(output_path)
        
        logger.info(f"PDF 报告已生成: {output_path}")
        return True
        
    except ImportError as e:
        logger.warning(f"依赖缺失，无法生成 PDF: {e}")
        return False
    except Exception as e:
        logger.error(f"从 Markdown 生成 PDF 失败: {e}")
        return False
