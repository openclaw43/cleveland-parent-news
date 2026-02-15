import feedparser
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RSSFeedParser:
    def __init__(self, rate_limit_delay: float = 1.0, timeout: int = 30):
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.last_request_time = 0

    def _rate_limit(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _generate_article_id(self, url: str, title: str) -> str:
        content = f"{url}|{title}"
        return hashlib.md5(content.encode()).hexdigest()

    def parse_feed(self, feed_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        articles = []
        feed_name = feed_config.get('name', 'Unknown')
        feed_url = feed_config.get('url', '')
        category = feed_config.get('category', 'general')
        priority = feed_config.get('priority', 2)

        if not feed_url:
            logger.warning(f"No URL provided for feed: {feed_name}")
            return articles

        try:
            self._rate_limit()
            logger.info(f"Fetching RSS feed: {feed_name} - {feed_url}")
            
            feed = feedparser.parse(
                feed_url,
                request_headers={'User-Agent': 'ClevelandParentNews/1.0'}
            )

            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning for {feed_name}: {feed.bozo_exception}")

            for entry in feed.entries:
                try:
                    article = self._parse_entry(entry, feed_name, category, priority)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Error parsing entry in {feed_name}: {e}")
                    continue

            logger.info(f"Parsed {len(articles)} articles from {feed_name}")

        except Exception as e:
            logger.error(f"Error fetching feed {feed_name}: {e}")

        return articles

    def _parse_entry(self, entry: Any, source: str, category: str, priority: int) -> Optional[Dict[str, Any]]:
        title = entry.get('title', '')
        if not title:
            return None

        url = entry.get('link', '')
        description = entry.get('description', entry.get('summary', ''))
        
        published = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                published = datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass

        if not published:
            published = datetime.now()

        content = ''
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].get('value', '')
        elif hasattr(entry, 'summary_detail'):
            content = entry.summary_detail.get('value', '')

        return {
            'id': self._generate_article_id(url, title),
            'title': title,
            'url': url,
            'description': description,
            'content': content,
            'source': source,
            'category': category,
            'priority': priority,
            'published_at': published.isoformat() if published else None,
            'collected_at': datetime.now().isoformat(),
            'type': 'rss'
        }

    def parse_all_feeds(self, feeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        all_articles = []
        for feed_config in feeds:
            articles = self.parse_feed(feed_config)
            all_articles.extend(articles)
        return all_articles


def main():
    import yaml
    
    with open('config/sources.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    parser = RSSFeedParser(rate_limit_delay=1.0)
    articles = parser.parse_all_feeds(config.get('rss_feeds', []))
    
    print(f"\nCollected {len(articles)} articles from RSS feeds")
    for article in articles[:5]:
        print(f"- [{article['source']}] {article['title']}")


if __name__ == '__main__':
    main()
