"""
Publisher module for Cleveland Parent News.

Supports:
- Email via SMTP (Mailgun, SendGrid, Gmail, etc.)
- Substack via python-substack (unofficial API)
- Manual output for copy-paste
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailPublisher:
    """Publish newsletter via SMTP email."""
    
    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = 587,
        username: str = None,
        password: str = None,
        from_email: str = None,
        from_name: str = "Cleveland Parent News"
    ):
        self.smtp_host = smtp_host or os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', 587))
        self.username = username or os.getenv('SMTP_USERNAME')
        self.password = password or os.getenv('SMTP_PASSWORD')
        self.from_email = from_email or os.getenv('FROM_EMAIL', self.username)
        self.from_name = from_name
    
    def send_newsletter(
        self,
        html_content: str,
        text_content: str,
        subject: str,
        to_emails: List[str]
    ) -> bool:
        """Send newsletter via email."""
        if not all([self.username, self.password]):
            logger.error("SMTP credentials not configured")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = ', '.join(to_emails)
        
        # Attach both plain text and HTML
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            logger.info(f"Newsletter sent to {len(to_emails)} recipients")
            return True
        except Exception as e:
            logger.error(f"Failed to send newsletter: {e}")
            return False


class SubstackPublisher:
    """Publish to Substack via python-substack library."""
    
    def __init__(
        self,
        email: str = None,
        password: str = None,
        publication_url: str = None
    ):
        self.email = email or os.getenv('SUBSTACK_EMAIL')
        self.password = password or os.getenv('SUBSTACK_PASSWORD')
        self.publication_url = publication_url or os.getenv('SUBSTACK_PUBLICATION_URL')
        self.api = None
    
    def _get_api(self):
        """Initialize Substack API."""
        if self.api:
            return self.api
        
        try:
            from substack import Api
            self.api = Api(
                email=self.email,
                password=self.password,
                publication_url=self.publication_url
            )
            return self.api
        except ImportError:
            logger.error("python-substack not installed. Run: uv add python-substack")
            raise
    
    def publish_post(
        self,
        title: str,
        subtitle: str,
        content_blocks: List[Dict[str, Any]],
        publish: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Publish a post to Substack.
        
        Args:
            title: Post title
            subtitle: Post subtitle
            content_blocks: List of content blocks [{'type': 'paragraph', 'content': '...'}]
            publish: If True, publishes immediately. If False, creates draft.
        
        Returns:
            Draft/published post data or None on failure
        """
        try:
            from substack.post import Post
            
            api = self._get_api()
            
            post = Post(
                title=title,
                subtitle=subtitle,
                user_id="1"  # Usually works as default
            )
            
            for block in content_blocks:
                post.add(block)
            
            # Create draft
            draft = api.post_draft(post.get_draft())
            draft_id = draft.get("id")
            
            if publish:
                api.prepublish_draft(draft_id)
                result = api.publish_draft(draft_id)
                logger.info(f"Published to Substack: {title}")
            else:
                result = draft
                logger.info(f"Created Substack draft: {title}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to publish to Substack: {e}")
            return None
    
    def convert_markdown_to_blocks(self, markdown_text: str) -> List[Dict[str, Any]]:
        """Convert markdown newsletter to Substack content blocks."""
        blocks = []
        
        lines = markdown_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Headings
            if line.startswith('# '):
                # Skip main title (already in post object)
                i += 1
                continue
            elif line.startswith('## '):
                blocks.append({
                    'type': 'heading',
                    'content': line[3:].strip()
                })
            elif line.startswith('---'):
                # Horizontal rule / divider
                pass
            elif line.startswith('!['):
                # Images (would need URL extraction)
                pass
            elif line.startswith('[') and '](' in line:
                # Links - extract as link
                import re
                match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', line)
                if match:
                    text, url = match.groups()
                    blocks.append({
                        'type': 'paragraph',
                        'content': f'<a href="{url}">{text}</a>'
                    })
                else:
                    blocks.append({'type': 'paragraph', 'content': line})
            elif line:
                # Regular paragraph
                blocks.append({
                    'type': 'paragraph',
                    'content': line
                })
            
            i += 1
        
        return blocks


class ManualPublisher:
    """Save newsletter for manual copy-paste."""
    
    def save_for_manual(
        self,
        title: str,
        subtitle: str,
        markdown_content: str,
        html_content: str,
        output_dir: str = 'data/processed'
    ) -> Dict[str, str]:
        """Save newsletter files for manual publishing."""
        import os
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Markdown for Substack
        md_path = os.path.join(output_dir, f'newsletter_{timestamp}.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(f"*{subtitle}*\n\n")
            f.write(markdown_content)
        
        # HTML for email
        html_path = os.path.join(output_dir, f'newsletter_{timestamp}.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Plain text version
        txt_path = os.path.join(output_dir, f'newsletter_{timestamp}.txt')
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"{title}\n")
            f.write(f"{subtitle}\n\n")
            # Simple stripping of markdown
            import re
            plain = re.sub(r'[#*_\[\]()]', '', markdown_content)
            f.write(plain)
        
        logger.info(f"Saved newsletter for manual publishing:")
        logger.info(f"  Markdown: {md_path}")
        logger.info(f"  HTML: {html_path}")
        logger.info(f"  Text: {txt_path}")
        
        return {
            'markdown': md_path,
            'html': html_path,
            'text': txt_path
        }


# Example usage
if __name__ == '__main__':
    # 1. Manual publishing (always works)
    manual = ManualPublisher()
    manual.save_for_manual(
        title="Cleveland Parent News - Issue #1",
        subtitle="Weekly roundup for Cleveland families",
        markdown_content="# Test Article\n\nThis is a test.",
        html_content="<h1>Test Article</h1><p>This is a test.</p>"
    )
    
    # 2. Email (requires SMTP env vars)
    # email_pub = EmailPublisher()
    # email_pub.send_newsletter(
    #     html_content="<h1>Test</h1>",
    #     text_content="Test",
    #     subject="Newsletter Test",
    #     to_emails=["test@example.com"]
    # )
    
    # 3. Substack (requires SUBSTACK_EMAIL, SUBSTACK_PASSWORD, SUBSTACK_PUBLICATION_URL)
    # substack_pub = SubstackPublisher()
    # substack_pub.publish_post(
    #     title="Test Post",
    #     subtitle="Test subtitle",
    #     content_blocks=[
    #         {'type': 'paragraph', 'content': 'Hello world'}
    #     ],
    #     publish=False  # Draft only
    # )
