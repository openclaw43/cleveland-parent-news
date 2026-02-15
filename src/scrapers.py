import requests
from bs4 import BeautifulSoup
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebScraper:
    def __init__(self, rate_limit_delay: float = 1.0, timeout: int = 30):
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def _rate_limit(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _generate_article_id(self, url: str, title: str) -> str:
        content = f"{url}|{title}"
        return hashlib.md5(content.encode()).hexdigest()

    def _clean_text(self, text: str) -> str:
        if not text:
            return ''
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        try:
            self._rate_limit()
            logger.info(f"Fetching page: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            return BeautifulSoup(response.content, 'html.parser')
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def scrape_source(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        articles = []
        source_name = source_config.get('name', 'Unknown')
        source_url = source_config.get('url', '')
        source_type = source_config.get('type', 'news')
        priority = source_config.get('priority', 2)
        selectors = source_config.get('selectors', {})

        if not source_url:
            logger.warning(f"No URL provided for scraper: {source_name}")
            return articles

        soup = self.fetch_page(source_url)
        if not soup:
            return articles

        container_selector = selectors.get('event_container') or selectors.get('article_container')
        if not container_selector:
            logger.warning(f"No container selector for {source_name}")
            return articles

        try:
            containers = soup.select(container_selector)
            logger.info(f"Found {len(containers)} items in {source_name}")

            for container in containers:
                try:
                    article = self._extract_item(
                        container, selectors, source_name, source_type, priority
                    )
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Error extracting item from {source_name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing {source_name}: {e}")

        return articles

    def _extract_item(
        self, 
        container: BeautifulSoup, 
        selectors: Dict[str, str],
        source: str,
        source_type: str,
        priority: int
    ) -> Optional[Dict[str, Any]]:
        title_selector = selectors.get('title', 'h2, h3, .title')
        date_selector = selectors.get('date', '.date, time')
        description_selector = selectors.get('description', 'p, .summary')
        link_selector = selectors.get('link', 'a')

        title_elem = container.select_one(title_selector)
        title = self._clean_text(title_elem.get_text()) if title_elem else ''

        if not title:
            return None

        date_elem = container.select_one(date_selector)
        date_text = self._clean_text(date_elem.get_text()) if date_elem else ''
        
        description_elem = container.select_one(description_selector)
        description = self._clean_text(description_elem.get_text()) if description_elem else ''

        link_elem = container.select_one(link_selector)
        url = ''
        if link_elem and link_elem.get('href'):
            url = link_elem['href']
            if url.startswith('/'):
                from urllib.parse import urljoin
                base_url = source.split('/')[0] + '//' + '/'.join(source.split('/')[2:3])
                url = urljoin(base_url, url)

        return {
            'id': self._generate_article_id(url, title),
            'title': title,
            'url': url,
            'description': description,
            'content': '',
            'source': source,
            'category': source_type,
            'priority': priority,
            'published_at': date_text or datetime.now().isoformat(),
            'collected_at': datetime.now().isoformat(),
            'type': 'scraper'
        }

    def scrape_all_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        all_articles = []
        for source_config in sources:
            articles = self.scrape_source(source_config)
            all_articles.extend(articles)
        return all_articles


def main():
    import yaml
    
    with open('config/sources.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    rate_config = config.get('rate_limiting', {})
    scraper = WebScraper(
        rate_limit_delay=rate_config.get('default_delay', 1.0),
        timeout=rate_config.get('timeout', 30)
    )
    
    articles = scraper.scrape_all_sources(config.get('scrapers', []))
    
    print(f"\nCollected {len(articles)} items from web scrapers")
    for article in articles[:5]:
        print(f"- [{article['source']}] {article['title']}")


if __name__ == '__main__':
    main()
