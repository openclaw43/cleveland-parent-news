import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from string import Template
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsletterGenerator:
    def __init__(self):
        self.newsletter_template = Template('''
# Cleveland Parent News

*Your weekly roundup of family-friendly news, events, and resources in Cleveland*

---

**Issue #${issue_number} | ${date}**

---

## 📚 Education & Schools

${education_section}

---

## 🎭 Family Events & Activities

${events_section}

---

## 🏞️ Parks & Recreation

${parks_section}

---

## 📚 Library & Learning

${library_section}

---

## 🏥 Health & Safety

${health_section}

---

## 📰 Local News for Parents

${news_section}

---

## Quick Links

- [Cleveland Metropolitan School District](https://www.clevelandmetroschools.org/)
- [Cleveland Public Library](https://cpl.org/)
- [Cleveland Metroparks](https://www.clevelandmetroparks.com/)
- [Cleveland Museum of Natural History](https://www.cmnh.org/)

---

*Cleveland Parent News is curated for families in the Greater Cleveland area.*

*Last updated: ${generated_at}*

---

*Want to submit an event or news tip? Reply to this newsletter!*
''')

    def _format_article_entry(self, article: Dict[str, Any], include_description: bool = True) -> str:
        title = article.get('title', 'Untitled')
        url = article.get('url', '')
        source = article.get('source', 'Unknown')
        description = article.get('description', '')
        
        entry = f"**{title}**"
        if url:
            entry = f"[{entry}]({url})"
        entry += f"\n*Source: {source}*"
        
        if include_description and description:
            desc_preview = description[:150] + '...' if len(description) > 150 else description
            entry += f"\n{desc_preview}"
        
        return entry

    def _categorize_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        categories = {
            'education': [],
            'events': [],
            'parks': [],
            'library': [],
            'health': [],
            'news': []
        }
        
        for article in articles:
            matched_keywords = [k.lower() for k in article.get('matched_keywords', [])]
            filter_category = article.get('filter_category', '')
            source = article.get('source', '').lower()
            description = article.get('description', '').lower()
            title = article.get('title', '').lower()
            
            all_text = f"{' '.join(matched_keywords)} {filter_category} {source} {description} {title}"
            
            if any(kw in all_text for kw in ['school', 'cmsd', 'education', 'teacher', 'student', 'classroom']):
                categories['education'].append(article)
            elif any(kw in all_text for kw in ['event', 'family fun', 'workshop', 'camp', 'storytime']):
                categories['events'].append(article)
            elif any(kw in all_text for kw in ['park', 'metroparks', 'zoo', 'playground', 'outdoor']):
                categories['parks'].append(article)
            elif any(kw in all_text for kw in ['library', 'reading', 'book', 'cpl']):
                categories['library'].append(article)
            elif any(kw in all_text for kw in ['health', 'safety', 'vaccination', 'hospital', 'clinic']):
                categories['health'].append(article)
            else:
                categories['news'].append(article)
        
        for cat in categories:
            categories[cat].sort(key=lambda x: x.get('filter_score', 0), reverse=True)
        
        return categories

    def _build_section(self, articles: List[Dict[str, Any]], max_items: int = 5) -> str:
        if not articles:
            return "*No items this week*"
        
        entries = []
        for article in articles[:max_items]:
            entries.append(self._format_article_entry(article))
        
        return '\n\n'.join(entries)

    def generate_newsletter(
        self,
        articles: List[Dict[str, Any]],
        issue_number: int = 1,
        max_items_per_section: int = 5
    ) -> str:
        categories = self._categorize_articles(articles)
        
        newsletter = self.newsletter_template.substitute(
            issue_number=issue_number,
            date=datetime.now().strftime('%B %d, %Y'),
            education_section=self._build_section(categories['education'], max_items_per_section),
            events_section=self._build_section(categories['events'], max_items_per_section),
            parks_section=self._build_section(categories['parks'], max_items_per_section),
            library_section=self._build_section(categories['library'], max_items_per_section),
            health_section=self._build_section(categories['health'], max_items_per_section),
            news_section=self._build_section(categories['news'], max_items_per_section),
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        return newsletter

    def generate_email_html(
        self,
        articles: List[Dict[str, Any]],
        issue_number: int = 1
    ) -> str:
        categories = self._categorize_articles(articles)
        
        html_sections = []
        
        section_configs = [
            ('📚 Education & Schools', 'education'),
            ('🎭 Family Events & Activities', 'events'),
            ('🏞️ Parks & Recreation', 'parks'),
            ('📖 Library & Learning', 'library'),
            ('🏥 Health & Safety', 'health'),
            ('📰 Local News for Parents', 'news')
        ]
        
        for title, category in section_configs:
            items = categories[category][:5]
            if items:
                section_html = f'''
                <h2 style="color: #2c5282; border-bottom: 2px solid #4299e1; padding-bottom: 10px;">{title}</h2>
                '''
                for article in items:
                    section_html += f'''
                    <div style="margin-bottom: 20px; padding: 15px; background-color: #f7fafc; border-radius: 8px;">
                        <h3 style="margin: 0 0 8px 0; color: #2d3748;">
                            <a href="{article.get('url', '#')}" style="color: #2b6cb0; text-decoration: none;">
                                {article.get('title', 'Untitled')}
                            </a>
                        </h3>
                        <p style="margin: 0; color: #718096; font-size: 14px;">
                            <em>Source: {article.get('source', 'Unknown')}</em>
                        </p>
                        <p style="margin: 8px 0 0 0; color: #4a5568; font-size: 14px;">
                            {article.get('description', '')[:200]}{'...' if len(article.get('description', '')) > 200 else ''}
                        </p>
                    </div>
                    '''
                html_sections.append(section_html)
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Cleveland Parent News - Issue #{issue_number}</title>
        </head>
        <body style="font-family: Georgia, 'Times New Roman', serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff;">
            <div style="text-align: center; padding: 30px 0; border-bottom: 3px solid #4299e1;">
                <h1 style="color: #2c5282; margin: 0;">Cleveland Parent News</h1>
                <p style="color: #718096; margin: 10px 0 0 0;">Your weekly roundup for Cleveland families</p>
                <p style="color: #4299e1; margin: 5px 0 0 0;">Issue #{issue_number} | {datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <div style="padding: 20px 0;">
                {''.join(html_sections)}
            </div>
            
            <div style="text-align: center; padding: 30px 0; border-top: 2px solid #e2e8f0; margin-top: 30px; color: #718096; font-size: 12px;">
                <p>Cleveland Parent News - Curated for families in Greater Cleveland</p>
                <p style="margin-top: 10px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        '''
        
        return html

    def generate_substack_post(
        self,
        articles: List[Dict[str, Any]],
        issue_number: int = 1
    ) -> Dict[str, str]:
        markdown = self.generate_newsletter(articles, issue_number)
        html = self.generate_email_html(articles, issue_number)
        
        title = f"Cleveland Parent News - Issue #{issue_number}"
        subtitle = f"Weekly roundup for Cleveland families - {datetime.now().strftime('%B %d, %Y')}"
        
        return {
            'title': title,
            'subtitle': subtitle,
            'body': markdown,
            'html': html
        }


def main():
    """Generate newsletter from database articles."""
    from .database import ArticleDatabase
    
    db = ArticleDatabase()
    
    # Get recent articles from last 7 days
    articles = db.get_articles(limit=30)
    
    if not articles:
        print("No articles found in database. Run 'uv run python -m src.collector' first.")
        return
    
    # Get issue number from database
    issue_number = db.get_collection_count() + 1
    
    generator = NewsletterGenerator()
    post = generator.generate_substack_post(articles, issue_number=issue_number)
    
    # Save outputs
    output_dir = 'data/processed'
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d')
    md_file = os.path.join(output_dir, f'newsletter_{timestamp}.md')
    html_file = os.path.join(output_dir, f'newsletter_{timestamp}.html')
    
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(post['body'])
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(post['html'])
    
    print(f"\n✅ Newsletter generated!")
    print(f"   Issue: #{issue_number}")
    print(f"   Articles: {len(articles)}")
    print(f"   Markdown: {md_file}")
    print(f"   HTML: {html_file}")
    print(f"\n--- PREVIEW ---\n")
    print(post['body'][:800] + "...\n[truncated for display]")


if __name__ == '__main__':
    main()
