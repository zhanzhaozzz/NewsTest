"""
内容存储管理器

将抓取到的新闻正文内容存储到 SQLite 数据库
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from .base import ScrapedContent

logger = logging.getLogger(__name__)


class ContentStore:
    """
    新闻正文内容存储器
    
    使用 SQLite 存储抓取到的新闻正文，支持：
    - 按 URL 存取内容
    - 设置过期时间
    - 避免重复抓取
    """
    
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS scraped_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE NOT NULL,
        url_hash TEXT NOT NULL,
        title TEXT,
        content TEXT,
        author TEXT,
        publish_time TEXT,
        word_count INTEGER DEFAULT 0,
        images TEXT,
        metadata TEXT,
        scraper_type TEXT,
        scraped_at TEXT NOT NULL,
        expires_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_url_hash ON scraped_content(url_hash);
    CREATE INDEX IF NOT EXISTS idx_scraped_at ON scraped_content(scraped_at);
    CREATE INDEX IF NOT EXISTS idx_expires_at ON scraped_content(expires_at);
    """
    
    def __init__(self, db_path: str = None, retention_days: int = 7):
        """
        初始化内容存储器
        
        Args:
            db_path: 数据库文件路径，默认为 data/content.db
            retention_days: 内容保留天数
        """
        if db_path is None:
            db_path = Path("data") / "content.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.retention_days = retention_days
        
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self.CREATE_TABLE_SQL)
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _hash_url(self, url: str) -> str:
        """生成 URL 的哈希值"""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()
    
    def save(self, content: ScrapedContent, scraper_type: str = None) -> bool:
        """
        保存抓取的内容
        
        Args:
            content: 抓取到的内容
            scraper_type: 使用的抓取器类型
            
        Returns:
            bool: 是否保存成功
        """
        try:
            now = datetime.now()
            expires_at = now + timedelta(days=self.retention_days)
            
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO scraped_content 
                    (url, url_hash, title, content, author, publish_time, 
                     word_count, images, metadata, scraper_type, scraped_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    content.url,
                    self._hash_url(content.url),
                    content.title,
                    content.content,
                    content.author,
                    content.publish_time.isoformat() if content.publish_time else None,
                    content.word_count,
                    json.dumps(content.images),
                    json.dumps(content.metadata),
                    scraper_type,
                    now.isoformat(),
                    expires_at.isoformat(),
                ))
                conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"保存内容失败: {e}")
            return False
    
    def get(self, url: str) -> Optional[ScrapedContent]:
        """
        获取 URL 对应的内容
        
        Args:
            url: 新闻 URL
            
        Returns:
            ScrapedContent 或 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM scraped_content 
                    WHERE url_hash = ? AND (expires_at IS NULL OR expires_at > ?)
                """, (self._hash_url(url), datetime.now().isoformat()))
                
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_content(row)
                
                return None
                
        except Exception as e:
            logger.error(f"获取内容失败: {e}")
            return None
    
    def exists(self, url: str) -> bool:
        """
        检查 URL 是否已经抓取过（且未过期）
        
        Args:
            url: 新闻 URL
            
        Returns:
            bool: 是否存在
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 1 FROM scraped_content 
                    WHERE url_hash = ? AND (expires_at IS NULL OR expires_at > ?)
                    LIMIT 1
                """, (self._hash_url(url), datetime.now().isoformat()))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"检查内容存在失败: {e}")
            return False
    
    def get_batch(self, urls: List[str]) -> Dict[str, ScrapedContent]:
        """
        批量获取多个 URL 的内容
        
        Args:
            urls: URL 列表
            
        Returns:
            Dict[str, ScrapedContent]: URL -> 内容 的映射
        """
        if not urls:
            return {}
        
        results = {}
        
        try:
            hashes = [self._hash_url(url) for url in urls]
            placeholders = ','.join(['?'] * len(hashes))
            
            with self._get_connection() as conn:
                cursor = conn.execute(f"""
                    SELECT * FROM scraped_content 
                    WHERE url_hash IN ({placeholders}) 
                    AND (expires_at IS NULL OR expires_at > ?)
                """, (*hashes, datetime.now().isoformat()))
                
                for row in cursor:
                    content = self._row_to_content(row)
                    if content:
                        results[content.url] = content
            
        except Exception as e:
            logger.error(f"批量获取内容失败: {e}")
        
        return results
    
    def filter_new_urls(self, urls: List[str]) -> List[str]:
        """
        过滤出未抓取过的 URL
        
        Args:
            urls: URL 列表
            
        Returns:
            List[str]: 未抓取过的 URL 列表
        """
        if not urls:
            return []
        
        existing = self.get_batch(urls)
        return [url for url in urls if url not in existing]
    
    def cleanup_expired(self) -> int:
        """
        清理过期内容
        
        Returns:
            int: 删除的记录数
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM scraped_content 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                """, (datetime.now().isoformat(),))
                
                deleted = cursor.rowcount
                conn.commit()
                
                logger.info(f"清理了 {deleted} 条过期内容")
                return deleted
                
        except Exception as e:
            logger.error(f"清理过期内容失败: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            with self._get_connection() as conn:
                # 总记录数
                total = conn.execute("SELECT COUNT(*) FROM scraped_content").fetchone()[0]
                
                # 今日新增
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_count = conn.execute("""
                    SELECT COUNT(*) FROM scraped_content 
                    WHERE scraped_at >= ?
                """, (today.isoformat(),)).fetchone()[0]
                
                # 数据库大小
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return {
                    'total_records': total,
                    'today_added': today_count,
                    'db_size_mb': round(db_size / 1024 / 1024, 2),
                    'retention_days': self.retention_days,
                }
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def _row_to_content(self, row: sqlite3.Row) -> Optional[ScrapedContent]:
        """将数据库行转换为 ScrapedContent"""
        try:
            publish_time = None
            if row['publish_time']:
                try:
                    publish_time = datetime.fromisoformat(row['publish_time'])
                except Exception:
                    pass
            
            images = []
            if row['images']:
                try:
                    images = json.loads(row['images'])
                except Exception:
                    pass
            
            metadata = {}
            if row['metadata']:
                try:
                    metadata = json.loads(row['metadata'])
                except Exception:
                    pass
            
            return ScrapedContent(
                url=row['url'],
                title=row['title'] or "",
                content=row['content'] or "",
                author=row['author'] or "",
                publish_time=publish_time,
                word_count=row['word_count'] or 0,
                images=images,
                metadata=metadata,
            )
            
        except Exception as e:
            logger.error(f"转换内容失败: {e}")
            return None
