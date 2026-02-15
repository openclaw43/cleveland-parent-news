"""Cleveland Parent News - Main workflow orchestrator."""

import os
import sys
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.collector import NewsCollector
from src.newsletter import NewsletterGenerator
from src.publisher import ManualPublisher, EmailPublisher, SubstackPublisher
from src.database import ArticleDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect():
    """Run the news collector."""
    logger.info("=" * 60)
    logger.info("Starting: Collect news")
    logger.info("=" * 60)
    
    collector = NewsCollector()
    result = collector.run_collection(save_raw=True)
    
    print(f"\n✅ Collection complete!")
    print(f"   Total articles: {result['total_collected']}")
    print(f"   Relevant: {result['relevant_articles']}")
    print(f"   Database: {result['database_inserted']}")
    
    return result


def generate(publish: bool = False):
    """Generate newsletter from collected articles."""
    logger.info("=" * 60)
    logger.info("Starting: Generate newsletter")
    logger.info("=" * 60)
    
    db = ArticleDatabase()
    generator = NewsletterGenerator()
    
    # Get recent articles
    articles = db.get_articles(limit=30)
    
    if not articles:
        logger.error("No articles found. Run 'collect' first.")
        return None
    
    # Get issue number
    issue_number = db.get_collection_count()
    
    # Generate newsletter
    post = generator.generate_substack_post(articles, issue_number=issue_number)
    
    # Save outputs
    manual = ManualPublisher()
    files = manual.save_for_manual(
        title=post['title'],
        subtitle=post['subtitle'],
        markdown_content=post['body'],
        html_content=post['html']
    )
    
    print(f"\n✅ Newsletter generated!")
    print(f"   Issue: #{issue_number}")
    print(f"   Articles: {len(articles)}")
    print(f"   Files: {len(files)}")
    
    if publish:
        return publish_newsletter(post, files)
    
    return post, files


def publish_newsletter(post: dict, files: dict) -> bool:
    """Publish newsletter via configured method."""
    logger.info("=" * 60)
    logger.info("Starting: Publish newsletter")
    logger.info("=" * 60)
    
    # Check for Substack credentials
    if os.getenv('SUBSTACK_EMAIL') and os.getenv('SUBSTACK_PASSWORD'):
        logger.info("Publishing to Substack...")
        publisher = SubstackPublisher()
        
        # Convert markdown to blocks
        blocks = publisher.convert_markdown_to_blocks(post['body'])
        
        result = publisher.publish_post(
            title=post['title'],
            subtitle=post['subtitle'],
            content_blocks=blocks,
            publish=True
        )
        
        if result:
            print(f"\n✅ Published to Substack!")
            return True
        else:
            print(f"\n❌ Substack publish failed. Check logs.")
            return False
    
    # Check for SMTP credentials
    elif os.getenv('SMTP_USERNAME') and os.getenv('SMTP_PASSWORD'):
        logger.info("Publishing via email...")
        publisher = EmailPublisher()
        
        # Load subscriber list
        subscribers = os.getenv('SUBSCRIBER_EMAILS', '').split(',')
        subscribers = [s.strip() for s in subscribers if s.strip()]
        
        if not subscribers:
            logger.error("No subscribers configured. Set SUBSCRIBER_EMAILS env var.")
            return False
        
        success = publisher.send_newsletter(
            html_content=post['html'],
            text_content=open(files['text']).read(),
            subject=post['title'],
            to_emails=subscribers
        )
        
        if success:
            print(f"\n✅ Sent to {len(subscribers)} subscribers!")
            return True
        else:
            print(f"\n❌ Email send failed. Check logs.")
            return False
    
    else:
        logger.info("No publishing credentials found.")
        print(f"\n📄 Newsletter saved for manual publishing.")
        print(f"   Markdown: {files['markdown']}")
        print(f"   Copy this to Substack manually.")
        return True


def stats():
    """Show database stats."""
    db = ArticleDatabase()
    stats = db.get_stats()
    
    print("\n📊 Database Statistics")
    print("=" * 40)
    print(f"Total articles: {stats['total_articles']}")
    print(f"Relevant articles: {stats['relevant_articles']}")
    print(f"Last collection: {stats['last_collection']}")
    
    if stats['by_source']:
        print("\nBy Source:")
        for source, count in stats['by_source'].items():
            print(f"  {source}: {count}")
    
    if stats['by_relevance']:
        print("\nBy Relevance:")
        for level, count in stats['by_relevance'].items():
            print(f"  {level}: {count}")


def main():
    """Main entry point with CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Cleveland Parent News - Collector & Publisher'
    )
    parser.add_argument(
        'command',
        choices=['collect', 'generate', 'publish', 'full', 'stats'],
        help='Command to run'
    )
    parser.add_argument(
        '--publish',
        action='store_true',
        help='Auto-publish after generating (for generate/full commands)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'collect':
        collect()
    
    elif args.command == 'generate':
        generate(publish=args.publish)
    
    elif args.command == 'publish':
        # Re-generate and publish
        post, files = generate(publish=False)
        if post:
            publish_newsletter(post, files)
    
    elif args.command == 'full':
        # Full pipeline
        result = collect()
        if result['relevant_articles'] > 0:
            post, files = generate(publish=False)
            if post:
                publish_newsletter(post, files)
    
    elif args.command == 'stats':
        stats()


if __name__ == '__main__':
    main()
