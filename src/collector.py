import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import yaml

from .rss_feeds import RSSFeedParser
from .scrapers import WebScraper
from .filters import ContentFilter
from .database import ArticleDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsCollector:
    def __init__(self, config_path: str = 'config/sources.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        
        rate_config = self.config.get('rate_limiting', {})
        rate_delay = rate_config.get('default_delay', 1.0)
        timeout = rate_config.get('timeout', 30)
        
        self.rss_parser = RSSFeedParser(rate_limit_delay=rate_delay, timeout=timeout)
        self.web_scraper = WebScraper(rate_limit_delay=rate_delay, timeout=timeout)
        self.content_filter = ContentFilter(self.config.get('parent_keywords', {}))
        self.database = ArticleDatabase()
        
        self.raw_dir = 'data/raw'
        self.processed_dir = 'data/processed'
        
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def _save_to_json(self, data: Any, filepath: str) -> None:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Saved data to {filepath}")
        except Exception as e:
            logger.error(f"Error saving to {filepath}: {e}")

    def collect_rss_feeds(self) -> List[Dict[str, Any]]:
        logger.info("Starting RSS feed collection...")
        feeds = self.config.get('rss_feeds', [])
        articles = self.rss_parser.parse_all_feeds(feeds)
        logger.info(f"Collected {len(articles)} articles from RSS feeds")
        return articles

    def collect_scraped_content(self) -> List[Dict[str, Any]]:
        logger.info("Starting web scraping...")
        sources = self.config.get('scrapers', [])
        items = self.web_scraper.scrape_all_sources(sources)
        logger.info(f"Scraped {len(items)} items from web sources")
        return items

    def process_articles(self, articles: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        logger.info("Filtering articles for parent relevance...")
        relevant, filtered_out = self.content_filter.filter_articles(articles)
        logger.info(f"Found {len(relevant)} relevant articles")
        return relevant, filtered_out

    def run_collection(self, save_raw: bool = True) -> Dict[str, Any]:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        logger.info("=" * 50)
        logger.info(f"Starting news collection run at {timestamp}")
        logger.info("=" * 50)
        
        rss_articles = self.collect_rss_feeds()
        scraped_items = self.collect_scraped_content()
        
        all_content = rss_articles + scraped_items
        
        if save_raw and all_content:
            raw_file = os.path.join(self.raw_dir, f'raw_{timestamp}.json')
            self._save_to_json(all_content, raw_file)
        
        relevant, filtered_out = self.process_articles(all_content)
        
        if relevant:
            processed_file = os.path.join(self.processed_dir, f'processed_{timestamp}.json')
            self._save_to_json(relevant, processed_file)
        
        inserted = self.database.insert_articles(relevant)
        
        self.database.log_collection_run(
            rss_count=len(rss_articles),
            scraped_count=len(scraped_items),
            filtered_count=len(relevant)
        )
        
        filter_summary = self.content_filter.get_filter_summary(relevant)
        
        result = {
            'timestamp': timestamp,
            'total_collected': len(all_content),
            'rss_articles': len(rss_articles),
            'scraped_items': len(scraped_items),
            'relevant_articles': len(relevant),
            'filtered_out': len(filtered_out),
            'database_inserted': inserted,
            'filter_summary': filter_summary,
            'raw_file': f'{self.raw_dir}/raw_{timestamp}.json' if save_raw and all_content else None,
            'processed_file': f'{self.processed_dir}/processed_{timestamp}.json' if relevant else None
        }
        
        logger.info("=" * 50)
        logger.info("Collection run complete!")
        logger.info(f"  Total collected: {result['total_collected']}")
        logger.info(f"  Relevant articles: {result['relevant_articles']}")
        logger.info(f"  Database inserted: {result['database_inserted']}")
        logger.info("=" * 50)
        
        return result

    def get_newsletter_content(
        self,
        limit: int = 20,
        min_relevance: str = 'medium'
    ) -> List[Dict[str, Any]]:
        relevance_levels = ['high', 'medium', 'low']
        min_idx = relevance_levels.index(min_relevance) if min_relevance in relevance_levels else 1
        allowed_levels = relevance_levels[:min_idx + 1]
        
        articles = self.database.get_articles(limit=limit)
        
        return [
            a for a in articles 
            if a.get('relevance_level') in allowed_levels
        ]


def main():
    collector = NewsCollector()
    result = collector.run_collection()
    
    print(f"\nCollection Results:")
    print(f"  Timestamp: {result['timestamp']}")
    print(f"  Total collected: {result['total_collected']}")
    print(f"  RSS articles: {result['rss_articles']}")
    print(f"  Scraped items: {result['scraped_items']}")
    print(f"  Relevant articles: {result['relevant_articles']}")
    
    if result['filter_summary'].get('top_keywords'):
        print(f"\nTop keywords:")
        for kw, count in list(result['filter_summary']['top_keywords'].items())[:5]:
            print(f"    {kw}: {count}")


if __name__ == '__main__':
    main()
