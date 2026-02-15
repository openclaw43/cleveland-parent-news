# Publishing Options for Cleveland Parent News

## Option 1: Substack (via python-substack)

**Library:** `python-substack` (unofficial, but works)

**Setup:**
```bash
uv add python-substack python-dotenv
```

**Usage:**
```python
from substack import Api
from substack.post import Post

api = Api(
    email="your@email.com",
    password="your-password",
    publication_url="https://clevelandparentnews.substack.com",
)

post = Post(
    title="Cleveland Parent News - Issue #1",
    subtitle="Weekly roundup for Cleveland families",
    user_id="1"  # Usually "1" works
)

post.add({'type': 'paragraph', 'content': 'Your content here'})

draft = api.post_draft(post.get_draft())
api.publish_draft(draft.get("id"))
```

**Pros:**
- Native Substack integration
- Handles formatting automatically
- Built-in subscriber management

**Cons:**
- Unofficial API (could break)
- Requires login credentials
- Limited customization

---

## Option 2: Email Newsletter (Recommended)

Use any email service (Mailgun, SendGrid, AWS SES, or your own SMTP).

**Setup:**
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_newsletter(html_content, to_emails, subject):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = 'newsletter@clevelandparentnews.com'
    msg['To'] = ', '.join(to_emails)
    
    msg.attach(MIMEText(html_content, 'html'))
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('your-email@gmail.com', 'app-password')
        server.send_message(msg)
```

**Services:**
- **Mailgun** - 5,000 free emails/month
- **SendGrid** - 100 emails/day free
- **AWS SES** - 62,000 free emails/month (from EC2)
- **Gmail SMTP** - 500 emails/day

**Pros:**
- Full control over content & design
- No platform lock-in
- Lower cost at scale
- Works with any email client

**Cons:**
- Need to manage subscriber list
- Spam folder risk
- Manual unsubscribe handling

---

## Option 3: Zapier/Make Integration

Connect your generated newsletter to Substack via automation:

1. **Collector saves** newsletter to `data/processed/newsletter_latest.md`
2. **Zapier watches** that file (or GitHub commit)
3. **Zapier posts** to Substack via their integration

**Pros:** No code needed
**Cons:** Paid service ($20-50/month), delays

---

## Option 4: Manual Copy-Paste

Generate newsletter → Open Substack editor → Copy markdown.

**Best for:** Getting started, quality control

---

## Recommendation

**Start with:** Email (Option 2) via Mailgun or Gmail SMTP
- Easier to test
- Full control
- Can migrate to Substack later

**Scale with:** Substack (Option 1)
- Once you validate the concept
- Use `python-substack` for automation
- Keep email list as backup

---

## Implementation

See `src/publisher.py` for working code examples.
