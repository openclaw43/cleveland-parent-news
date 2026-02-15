"""Browser-based scraper using Playwright for JavaScript-rendered sites."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class BrowserScraper:
    """Scraper using Playwright for JS-rendered pages."""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self._playwright = None
        self._browser = None
        
    def _init_browser(self):
        """Initialize Playwright browser."""
        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise
    
    def _close_browser(self):
        """Close browser resources."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("Browser closed")
    
    def _generate_id(self, url: str, title: str) -> str:
        content = f"{url}|{title}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def scrape_page(self, scraper_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape a single page using browser."""
        if not self._browser:
            self._init_browser()
            
        items = []
        name = scraper_config.get('name', 'Unknown')
        url = scraper_config.get('url', '')
        selectors = scraper_config.get('selectors', {})
        
        if not url:
            logger.warning(f"No URL for scraper: {name}")
            return items
            
        try:
            logger.info(f"Browser scraping: {name} - {url}")
            page = self._browser.new_page()
            page.goto(url, timeout=self.timeout, wait_until='networkidle')
            
            # Wait for content to load
            container_selector = selectors.get('event_container', 'article')
            page.wait_for_selector(container_selector, timeout=self.timeout)
            
            # Extract items
            elements = page.query_selector_all(container_selector)
            logger.info(f"Found {len(elements)} items on {name}")
            
            for element in elements:
                try:
                    item = self._extract_item(element, selectors, name, scraper_config)
                    if item:
                        items.append(item)
                except Exception as e:
                    logger.error(f"Error extracting item from {name}: {e}")
                    continue
            
            page.close()
            
        except Exception as e:
            logger.error(f"Error scraping {name}: {e}")
            
        return items
    
    def _extract_item(self, element, selectors: Dict[str, str], source: str, config: Dict) -> Optional[Dict[str, Any]]:
        """Extract data from a single element."""
        title_elem = element.query_selector(selectors.get('title', 'h2'))
        date_elem = element.query_selector(selectors.get('date', '.date'))
        desc_elem = element.query_selector(selectors.get('description', '.description'))
        link_elem = element.query_selector(selectors.get('link', 'a'))
        
        title = title_elem.inner_text() if title_elem else ''
        if not title:
            return None
            
        url = link_elem.get_attribute('href') if link_elem else ''
        if url and not url.startswith('http'):
            base = config.get('url', '').split('/')[2]
            url = f"https://{base}{url}"
        
        date_text = date_elem.inner_text() if date_elem else ''
        description = desc_elem.inner_text() if desc_elem else ''
        
        return {
            'id': self._generate_id(url or source, title),
            'title': title.strip(),
            'url': url,
            'description': description.strip(),
            'content': description.strip(),
            'source': source,
            'category': config.get('category', 'events'),
            'priority': config.get('priority', 2),
            'published_at': date_text,
            'collected_at': datetime.now().isoformat(),
            'type': 'scraped'
        }
    
    def scrape_all(self, scraper_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scrape all configured sites with browser."""
        all_items = []
        
        try:
            for config in scraper_configs:
                if not config.get('enabled', True):
                    continue
                items = self.scrape_page(config)
                all_items.extend(items)
        finally:
            self._close_browser()
            
        return all_items


def main():
    """Test browser scraper."""
    import yaml
    
    with open('config/sources.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Only run browser scrapers marked as JS-rendered
    js_scrapers = [
        s for s in config.get('scrapers', [])
        if s.get('enabled') and 'JavaScript' in s.get('notes', '')
    ]
    
    if not js_scrapers:
        print("No JavaScript scrapers enabled")
        return
    
    scraper = BrowserScraper(headless=True)
    items = scraper.scrape_all(js_scrapers)
    
    print(f"\nScraped {len(items)} items with browser")
    for item in items[:5]:
        print(f"- [{item['source']}] {item['title']}")


if __name__ == '__main__':
    main()
