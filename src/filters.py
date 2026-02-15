import re
import logging
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FilterMatch:
    keyword: str
    category: str
    priority: int
    context: str


@dataclass
class FilterResult:
    is_relevant: bool
    score: float
    matches: List[FilterMatch] = field(default_factory=list)
    primary_category: str = ''
    relevance_level: str = 'low'


class ContentFilter:
    def __init__(self, keywords_config: Dict[str, Any]):
        self.high_priority_keywords: Set[str] = set(
            k.lower() for k in keywords_config.get('high_priority', [])
        )
        self.medium_priority_keywords: Set[str] = set(
            k.lower() for k in keywords_config.get('medium_priority', [])
        )
        self.event_keywords: Set[str] = set(
            k.lower() for k in keywords_config.get('event_keywords', [])
        )
        
        self.all_keywords = (
            self.high_priority_keywords | 
            self.medium_priority_keywords | 
            self.event_keywords
        )

    def _extract_context(self, text: str, keyword: str, context_length: int = 50) -> str:
        text_lower = text.lower()
        idx = text_lower.find(keyword)
        if idx == -1:
            return keyword
        
        start = max(0, idx - context_length)
        end = min(len(text), idx + len(keyword) + context_length)
        return '...' + text[start:end] + '...'

    def _calculate_score(self, matches: List[FilterMatch]) -> float:
        if not matches:
            return 0.0
        
        score = 0.0
        for match in matches:
            if match.priority == 1:
                score += 3.0
            elif match.priority == 2:
                score += 1.5
            else:
                score += 0.5
        
        unique_keywords = len(set(m.keyword for m in matches))
        score += unique_keywords * 0.5
        
        return min(score, 20.0)

    def _determine_relevance_level(self, score: float) -> str:
        if score >= 5.0:
            return 'high'
        elif score >= 2.0:
            return 'medium'
        elif score > 0:
            return 'low'
        return 'none'

    def _determine_primary_category(self, matches: List[FilterMatch]) -> str:
        if not matches:
            return 'general'
        
        category_counts: Dict[str, int] = {}
        for match in matches:
            category_counts[match.category] = category_counts.get(match.category, 0) + 1
        
        return max(category_counts, key=lambda k: category_counts[k])

    def filter_article(self, article: Dict[str, Any]) -> FilterResult:
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = article.get('content', '').lower()
        
        full_text = f"{title} {description} {content}"
        
        if len(full_text.strip()) < 10:
            return FilterResult(
                is_relevant=False,
                score=0.0,
                matches=[],
                primary_category='general',
                relevance_level='none'
            )
        
        matches: List[FilterMatch] = []

        for keyword in self.high_priority_keywords:
            pattern = r'\b' + re.escape(keyword) + r's?\b'
            if re.search(pattern, full_text):
                matches.append(FilterMatch(
                    keyword=keyword,
                    category='education_family',
                    priority=1,
                    context=self._extract_context(full_text, keyword)
                ))

        for keyword in self.medium_priority_keywords:
            pattern = r'\b' + re.escape(keyword) + r's?\b'
            if re.search(pattern, full_text):
                matches.append(FilterMatch(
                    keyword=keyword,
                    category='activities_health',
                    priority=2,
                    context=self._extract_context(full_text, keyword)
                ))

        for keyword in self.event_keywords:
            pattern = r'\b' + re.escape(keyword) + r's?\b'
            if re.search(pattern, full_text):
                matches.append(FilterMatch(
                    keyword=keyword,
                    category='events',
                    priority=2,
                    context=self._extract_context(full_text, keyword)
                ))

        score = self._calculate_score(matches)
        is_relevant = score > 0
        relevance_level = self._determine_relevance_level(score)
        primary_category = self._determine_primary_category(matches)

        return FilterResult(
            is_relevant=is_relevant,
            score=score,
            matches=matches,
            primary_category=primary_category,
            relevance_level=relevance_level
        )

    def filter_articles(self, articles: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        relevant_articles = []
        filtered_out = []
        
        for article in articles:
            result = self.filter_article(article)
            
            if result.is_relevant:
                article['filter_score'] = result.score
                article['filter_category'] = result.primary_category
                article['relevance_level'] = result.relevance_level
                article['matched_keywords'] = [m.keyword for m in result.matches]
                relevant_articles.append(article)
            else:
                filtered_out.append(article)
        
        relevant_articles.sort(key=lambda x: x.get('filter_score', 0), reverse=True)
        
        logger.info(f"Filtering complete: {len(relevant_articles)} relevant, {len(filtered_out)} filtered out")
        
        return relevant_articles, filtered_out

    def get_filter_summary(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {
            'total_articles': len(articles),
            'by_category': {},
            'by_relevance': {'high': 0, 'medium': 0, 'low': 0},
            'top_keywords': {},
            'by_source': {}
        }
        
        keyword_counts: Dict[str, int] = {}
        
        for article in articles:
            category = article.get('filter_category', 'general')
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            relevance = article.get('relevance_level', 'low')
            if relevance in summary['by_relevance']:
                summary['by_relevance'][relevance] += 1
            
            source = article.get('source', 'Unknown')
            summary['by_source'][source] = summary['by_source'].get(source, 0) + 1
            
            for keyword in article.get('matched_keywords', []):
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        summary['top_keywords'] = dict(sorted_keywords[:10])
        
        return summary


def main():
    import yaml
    
    with open('config/sources.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    content_filter = ContentFilter(config.get('parent_keywords', {}))
    
    test_articles = [
        {
            'title': 'CMSD Announces New School Safety Initiative',
            'description': 'Cleveland Metropolitan School District launches new safety program for students',
            'content': '',
            'source': 'Test'
        },
        {
            'title': 'Cleveland Metroparks Hosts Family Fun Day',
            'description': 'Free event for families with children at various park locations',
            'content': '',
            'source': 'Test'
        },
        {
            'title': 'Local Restaurant Opens New Location',
            'description': 'Popular dining spot expands to second location downtown',
            'content': '',
            'source': 'Test'
        }
    ]
    
    relevant, filtered = content_filter.filter_articles(test_articles)
    
    print(f"\nRelevant articles: {len(relevant)}")
    for article in relevant:
        print(f"- [{article['relevance_level']}] {article['title']} (score: {article['filter_score']})")
    
    print(f"\nFiltered out: {len(filtered)}")
    for article in filtered:
        print(f"- {article['title']}")


if __name__ == '__main__':
    main()
