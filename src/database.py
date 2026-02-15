import sqlite3
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArticleDatabase:
    def __init__(self, db_path: str = 'data/newsletter.db'):
        self.db_path = db_path
        self._init_database()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT,
                    description TEXT,
                    content TEXT,
                    source TEXT,
                    category TEXT,
                    priority INTEGER DEFAULT 2,
                    published_at TEXT,
                    collected_at TEXT,
                    article_type TEXT,
                    filter_score REAL DEFAULT 0,
                    filter_category TEXT,
                    relevance_level TEXT,
                    matched_keywords TEXT,
                    is_processed INTEGER DEFAULT 0,
                    is_sent INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_collected_at ON articles(collected_at)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_filter_score ON articles(filter_score)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_relevance_level ON articles(relevance_level)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_source ON articles(source)
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS collection_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    rss_articles INTEGER DEFAULT 0,
                    scraped_articles INTEGER DEFAULT 0,
                    filtered_articles INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed'
                )
            ''')
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    def insert_article(self, article: Dict[str, Any]) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO articles (
                        id, title, url, description, content, source,
                        category, priority, published_at, collected_at,
                        article_type, filter_score, filter_category,
                        relevance_level, matched_keywords, is_processed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    article.get('id'),
                    article.get('title'),
                    article.get('url'),
                    article.get('description'),
                    article.get('content'),
                    article.get('source'),
                    article.get('category'),
                    article.get('priority', 2),
                    article.get('published_at'),
                    article.get('collected_at'),
                    article.get('type'),
                    article.get('filter_score', 0),
                    article.get('filter_category'),
                    article.get('relevance_level'),
                    json.dumps(article.get('matched_keywords', []))
                ))
                
                conn.commit()
                return True
            
            except sqlite3.Error as e:
                logger.error(f"Error inserting article {article.get('id')}: {e}")
                return False

    def insert_articles(self, articles: List[Dict[str, Any]]) -> int:
        inserted = 0
        for article in articles:
            if self.insert_article(article):
                inserted += 1
        logger.info(f"Inserted {inserted} articles into database")
        return inserted

    def get_articles(
        self,
        limit: int = 100,
        relevance_level: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[str] = None,
        unprocessed_only: bool = False
    ) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM articles WHERE 1=1'
            params = []
            
            if relevance_level:
                query += ' AND relevance_level = ?'
                params.append(relevance_level)
            
            if source:
                query += ' AND source = ?'
                params.append(source)
            
            if since:
                query += ' AND collected_at >= ?'
                params.append(since)
            
            if unprocessed_only:
                query += ' AND is_processed = 0'
            
            query += ' ORDER BY filter_score DESC, collected_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            articles = []
            for row in rows:
                article = dict(row)
                article['matched_keywords'] = json.loads(article['matched_keywords'] or '[]')
                articles.append(article)
            
            return articles

    def mark_as_sent(self, article_ids: List[str]) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(article_ids))
            cursor.execute(
                f'UPDATE articles SET is_sent = 1 WHERE id IN ({placeholders})',
                article_ids
            )
            conn.commit()

    def log_collection_run(
        self,
        rss_count: int,
        scraped_count: int,
        filtered_count: int,
        status: str = 'completed'
    ) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO collection_runs (
                    run_at, rss_articles, scraped_articles, filtered_articles, status
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                rss_count,
                scraped_count,
                filtered_count,
                status
            ))
            conn.commit()
            return cursor.lastrowid

    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM articles')
            total_articles = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM articles 
                WHERE relevance_level IN ('high', 'medium')
            ''')
            relevant_articles = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT source, COUNT(*) as count 
                FROM articles 
                GROUP BY source 
                ORDER BY count DESC
            ''')
            by_source = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute('''
                SELECT relevance_level, COUNT(*) as count 
                FROM articles 
                GROUP BY relevance_level
            ''')
            by_relevance = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute('''
                SELECT collected_at FROM articles 
                ORDER BY collected_at DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            last_collection = row[0] if row else None
            
            return {
                'total_articles': total_articles,
                'relevant_articles': relevant_articles,
                'by_source': by_source,
                'by_relevance': by_relevance,
                'last_collection': last_collection
            }

    def cleanup_old_articles(self, days: int = 30) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM articles 
                WHERE collected_at < datetime('now', ?)
                AND is_sent = 1
            ''', (f'-{days} days',))
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted} old articles")
            return deleted


def main():
    db = ArticleDatabase()
    
    test_article = {
        'id': 'test123',
        'title': 'Test Article',
        'url': 'https://example.com/test',
        'description': 'Test description',
        'source': 'Test Source',
        'category': 'test',
        'filter_score': 5.0,
        'relevance_level': 'high'
    }
    
    db.insert_article(test_article)
    
    stats = db.get_stats()
    print(f"\nDatabase stats: {json.dumps(stats, indent=2)}")


if __name__ == '__main__':
    main()
